# Blender Add-on Template
# Contributor(s): Aaron Powell (aaron@lunadigital.tv)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import math

import bpy
from bpy.types import Operator

OPTIMIZED_UV_NAME = "Optimized_UV"
OPTIMIZED_IMAGE_SUFFIX = "_optimized_atlas"
OPTIMIZED_PACKED_IMAGE_SUFFIX = "_optimized_packed"
OPTIMIZED_MATERIAL_SUFFIX = "_Optimized"


def _polygon_uv_area(uv_layer, polygon):
    if uv_layer is None or len(polygon.loop_indices) < 3:
        return 0.0

    uvs = [uv_layer.data[loop_index].uv for loop_index in polygon.loop_indices]
    area = 0.0

    for index, uv in enumerate(uvs):
        next_uv = uvs[(index + 1) % len(uvs)]
        area += (uv.x * next_uv.y) - (next_uv.x * uv.y)

    return abs(area) * 0.5


def _mesh_uv_area(mesh, uv_layer):
    return sum(_polygon_uv_area(uv_layer, polygon) for polygon in mesh.polygons)


def _round_to_power_of_two(value):
    size = max(64, int(value))
    power = 1
    while power < size:
        power <<= 1
    return power


def _find_largest_source_image_size(obj):
    largest_size = 1024

    for material_slot in obj.material_slots:
        material = material_slot.material
        if material is None or not material.use_nodes or material.node_tree is None:
            continue

        for node in material.node_tree.nodes:
            if node.bl_idname != "ShaderNodeTexImage" or node.image is None:
                continue

            width, height = node.image.size
            largest_size = max(largest_size, width, height)

    return largest_size


def _calculate_target_texture_size(source_size, source_uv_area, packed_uv_area, minimum_size, maximum_size):
    if source_uv_area <= 0.0 or packed_uv_area <= 0.0:
        return max(minimum_size, min(source_size, maximum_size))

    density_preserving_size = source_size * math.sqrt(source_uv_area / packed_uv_area)
    target_size = _round_to_power_of_two(density_preserving_size)

    return max(minimum_size, min(target_size, maximum_size))


def _duplicate_active_uv_layer(mesh):
    source_uv_layer = mesh.uv_layers.active
    if source_uv_layer is None and mesh.uv_layers:
        source_uv_layer = mesh.uv_layers[0]

    if source_uv_layer is None:
        return None, None

    source_uv_name = source_uv_layer.name
    copied_uvs = [uv.uv.copy() for uv in source_uv_layer.data]

    existing_layer = mesh.uv_layers.get(OPTIMIZED_UV_NAME)
    if existing_layer is not None:
        mesh.uv_layers.remove(existing_layer)

    optimized_layer = mesh.uv_layers.new(name=OPTIMIZED_UV_NAME)
    for index, uv in enumerate(copied_uvs):
        optimized_layer.data[index].uv = uv

    mesh.uv_layers.active = optimized_layer
    mesh.uv_layers.active_render = optimized_layer

    return source_uv_name, optimized_layer


def _pack_active_uvs(obj, margin):
    view_layer = bpy.context.view_layer
    previous_active = view_layer.objects.active
    previous_mode = obj.mode

    try:
        view_layer.objects.active = obj
        obj.select_set(True)

        if obj.mode != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(margin=margin)

    finally:
        if obj.mode != previous_mode:
            try:
                bpy.ops.object.mode_set(mode=previous_mode)
            except RuntimeError:
                pass

        if previous_active is not None:
            view_layer.objects.active = previous_active


def _link_uv_to_unlinked_image_textures(nodes, links, uv_map_name):
    uv_node = nodes.new(type="ShaderNodeUVMap")
    uv_node.uv_map = uv_map_name
    uv_node.location = (-1000, 0)

    for node in nodes:
        if node == uv_node:
            continue
        if node.bl_idname != "ShaderNodeTexImage":
            continue
        if "Vector" not in node.inputs:
            continue
        if node.inputs["Vector"].is_linked:
            continue
        links.new(uv_node.outputs["UV"], node.inputs["Vector"])

    return uv_node


def _find_image_texture_nodes(nodes):
    texture_nodes = []

    for node in nodes:
        if node.bl_idname != "ShaderNodeTexImage":
            continue
        if node.image is None:
            continue
        texture_nodes.append(node)

    return texture_nodes


def _find_output_node(nodes):
    active_output = None
    for node in nodes:
        if node.bl_idname != "ShaderNodeOutputMaterial":
            continue
        if getattr(node, "is_active_output", False):
            return node
        if active_output is None:
            active_output = node
    return active_output


def _find_principled_nodes(nodes):
    return [node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"]


def _node_tree_uses_packed_texture(node_tree):
    if node_tree is None:
        return False

    nodes = node_tree.nodes
    for principled_node in _find_principled_nodes(nodes):
        for socket_name in ("Metallic", "Roughness"):
            if socket_name not in principled_node.inputs:
                continue
            if principled_node.inputs[socket_name].is_linked:
                return True

    return False


def _guess_packed_texture_nodes(nodes):
    texture_nodes = _find_image_texture_nodes(nodes)
    if not texture_nodes:
        return []

    packed_nodes = []

    for node in texture_nodes:
        image_name = node.image.name.lower()
        if "metal" in image_name and "rough" in image_name:
            packed_nodes.append(node)

    if packed_nodes:
        return packed_nodes

    principled_nodes = _find_principled_nodes(nodes)
    linked_nodes = []

    for principled_node in principled_nodes:
        for socket_name in ("Metallic", "Roughness"):
            if socket_name not in principled_node.inputs:
                continue
            socket = principled_node.inputs[socket_name]
            if not socket.is_linked:
                continue

            source_node = socket.links[0].from_node

            if source_node.bl_idname == "ShaderNodeSeparateRGB":
                image_input_name = "Image" if "Image" in source_node.inputs else None
                if image_input_name and source_node.inputs[image_input_name].is_linked:
                    image_node = source_node.inputs[image_input_name].links[0].from_node
                    if image_node.bl_idname == "ShaderNodeTexImage" and image_node.image is not None:
                        linked_nodes.append(image_node)

            elif source_node.bl_idname == "ShaderNodeSeparateColor":
                color_input_name = "Color" if "Color" in source_node.inputs else None
                if color_input_name and source_node.inputs[color_input_name].is_linked:
                    image_node = source_node.inputs[color_input_name].links[0].from_node
                    if image_node.bl_idname == "ShaderNodeTexImage" and image_node.image is not None:
                        linked_nodes.append(image_node)

            elif source_node.bl_idname == "ShaderNodeNormalMap":
                color_input_name = "Color" if "Color" in source_node.inputs else None
                if color_input_name and source_node.inputs[color_input_name].is_linked:
                    image_node = source_node.inputs[color_input_name].links[0].from_node
                    if image_node.bl_idname == "ShaderNodeTexImage" and image_node.image is not None:
                        linked_nodes.append(image_node)

            elif source_node.bl_idname == "ShaderNodeTexImage" and source_node.image is not None:
                linked_nodes.append(source_node)

    unique_nodes = []
    seen_names = set()
    for node in linked_nodes:
        key = node.name
        if key in seen_names:
            continue
        seen_names.add(key)
        unique_nodes.append(node)

    if unique_nodes:
        return unique_nodes

    return []


def _assign_bake_target_node(nodes, image, name):
    for node in nodes:
        node.select = False

    bake_node = nodes.new(type="ShaderNodeTexImage")
    bake_node.name = name
    bake_node.image = image
    bake_node.location = (-300, -500)
    bake_node.select = True
    nodes.active = bake_node
    return bake_node


def _prepare_color_bake_material(original_material, source_uv_name, target_image):
    if original_material is not None:
        bake_material = original_material.copy()
        bake_material.name = f"{original_material.name}_Optimized_Color_Bake_Target"
    else:
        bake_material = bpy.data.materials.new("UVOptimizer_Optimized_Color_Bake_Target")

    bake_material.use_nodes = True
    nodes = bake_material.node_tree.nodes
    links = bake_material.node_tree.links

    _link_uv_to_unlinked_image_textures(nodes, links, source_uv_name)
    _assign_bake_target_node(nodes, target_image, "Optimized_Color_Bake_Target")

    return bake_material


def _prepare_packed_bake_material(original_material, source_uv_name, target_image):
    if original_material is not None:
        bake_material = original_material.copy()
        bake_material.name = f"{original_material.name}_Optimized_Packed_Bake_Target"
    else:
        bake_material = bpy.data.materials.new("UVOptimizer_Optimized_Packed_Bake_Target")

    bake_material.use_nodes = True
    nodes = bake_material.node_tree.nodes
    links = bake_material.node_tree.links

    _link_uv_to_unlinked_image_textures(nodes, links, source_uv_name)

    packed_nodes = _guess_packed_texture_nodes(nodes)
    if not packed_nodes:
        raise RuntimeError("Could not find any image texture node driving Metallic or Roughness.")

    output_node = _find_output_node(nodes)
    if output_node is None:
        raise RuntimeError("Could not find a material output node for packed texture baking.")

    packed_texture_node = packed_nodes[0]
    if hasattr(packed_texture_node.image, "colorspace_settings"):
        packed_texture_node.image.colorspace_settings.name = "Non-Color"

    emission_node = nodes.new(type="ShaderNodeEmission")
    emission_node.location = (240, -300)
    links.new(packed_texture_node.outputs["Color"], emission_node.inputs["Color"])

    for node in nodes:
        if node.bl_idname == "ShaderNodeOutputMaterial" and node.inputs["Surface"].is_linked:
            while node.inputs["Surface"].links:
                links.remove(node.inputs["Surface"].links[0])

    links.new(emission_node.outputs["Emission"], output_node.inputs["Surface"])

    _assign_bake_target_node(nodes, target_image, "Optimized_Packed_Bake_Target")

    return bake_material


def _duplicate_material_with_replaced_images(original_material, uv_name, color_image, packed_image):
    if original_material is not None:
        optimized_material = original_material.copy()
        optimized_material.name = f"{original_material.name}{OPTIMIZED_MATERIAL_SUFFIX}"
    else:
        optimized_material = bpy.data.materials.new(name=f"UVOptimizer{OPTIMIZED_MATERIAL_SUFFIX}")

    optimized_material.use_nodes = True

    if hasattr(optimized_material, "blend_method"):
        optimized_material.blend_method = "OPAQUE"
    if hasattr(optimized_material, "shadow_method"):
        optimized_material.shadow_method = "OPAQUE"

    nodes = optimized_material.node_tree.nodes
    links = optimized_material.node_tree.links

    optimized_uv_node = nodes.new(type="ShaderNodeUVMap")
    optimized_uv_node.name = "Optimized UV Map"
    optimized_uv_node.uv_map = uv_name
    optimized_uv_node.location = (-1200, 0)

    packed_nodes = _guess_packed_texture_nodes(nodes)
    packed_node_names = {node.name for node in packed_nodes}

    for node in nodes:
        if node == optimized_uv_node:
            continue
        if node.bl_idname != "ShaderNodeTexImage":
            continue

        if node.name in packed_node_names:
            node.image = packed_image
            if hasattr(node.image, "colorspace_settings"):
                node.image.colorspace_settings.name = "Non-Color"
        else:
            node.image = color_image
            if hasattr(node.image, "colorspace_settings"):
                node.image.colorspace_settings.name = "sRGB"

        if "Vector" in node.inputs:
            while node.inputs["Vector"].is_linked:
                links.remove(node.inputs["Vector"].links[0])
            links.new(optimized_uv_node.outputs["UV"], node.inputs["Vector"])

    return optimized_material


def _restore_materials(obj, materials):
    obj.data.materials.clear()
    for material in materials:
        obj.data.materials.append(material)


def _remove_materials(materials):
    for material in materials:
        if material is not None and material.users == 0:
            bpy.data.materials.remove(material)


def _bake_color_pass(obj, bake_margin):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=bake_margin)


def _bake_emit_pass(obj, bake_margin):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="EMIT", margin=bake_margin)


class UVOPTIMIZER_OT_optimize_selected_mesh(Operator):
    bl_idname = "uv_optimizer.optimize_selected_mesh"
    bl_label = "Optimize UV and Texture for Selected Mesh"
    bl_description = "Repack UVs for the selected mesh and bake the original material textures into smaller atlases"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        obj = context.object
        mesh = obj.data
        scene = context.scene

        if not mesh.polygons:
            self.report({"ERROR"}, "Selected mesh has no polygons.")
            return {"CANCELLED"}

        if scene.uv_optimizer_max_texture_size < scene.uv_optimizer_min_texture_size:
            self.report({"ERROR"}, "Maximum texture size must be greater than or equal to minimum texture size.")
            return {"CANCELLED"}

        original_materials = [slot.material for slot in obj.material_slots]
        previous_engine = scene.render.engine
        previous_active = context.view_layer.objects.active
        previous_mode = obj.mode
        bake_materials = []

        try:
            if obj.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")

            context.view_layer.objects.active = obj
            obj.select_set(True)

            source_uv_name, optimized_uv_layer = _duplicate_active_uv_layer(mesh)
            if source_uv_name is None or optimized_uv_layer is None:
                self.report({"ERROR"}, "Mesh requires an existing UV map.")
                return {"CANCELLED"}

            source_uv_area = _mesh_uv_area(mesh, optimized_uv_layer)

            _pack_active_uvs(obj, scene.uv_optimizer_pack_margin)
            mesh.update()

            packed_uv_layer = mesh.uv_layers.get(OPTIMIZED_UV_NAME)
            packed_uv_area = _mesh_uv_area(mesh, packed_uv_layer)

            source_size = _find_largest_source_image_size(obj)
            target_size = _calculate_target_texture_size(
                source_size,
                source_uv_area,
                packed_uv_area,
                scene.uv_optimizer_min_texture_size,
                scene.uv_optimizer_max_texture_size,
            )

            color_bake_image = bpy.data.images.new(
                name=f"{obj.name}{OPTIMIZED_IMAGE_SUFFIX}",
                width=target_size,
                height=target_size,
                alpha=True,
                float_buffer=False,
            )
            color_bake_image.generated_color = (0.0, 0.0, 0.0, 1.0)

            packed_bake_image = bpy.data.images.new(
                name=f"{obj.name}{OPTIMIZED_PACKED_IMAGE_SUFFIX}",
                width=target_size,
                height=target_size,
                alpha=False,
                float_buffer=False,
            )
            packed_bake_image.generated_color = (0.0, 0.0, 0.0, 1.0)
            packed_bake_image.colorspace_settings.name = "Non-Color"

            if not obj.material_slots:
                obj.data.materials.append(None)

            current_materials = [slot.material for slot in obj.material_slots]

            color_bake_materials = []
            packed_bake_materials = []
            optimized_materials = []

            for material in current_materials:
                color_bake_material = _prepare_color_bake_material(
                    material,
                    source_uv_name,
                    color_bake_image,
                )

                packed_bake_material = None
                if material is not None and _node_tree_uses_packed_texture(material.node_tree):
                    packed_bake_material = _prepare_packed_bake_material(
                        material,
                        source_uv_name,
                        packed_bake_image,
                    )

                optimized_material = _duplicate_material_with_replaced_images(
                    material,
                    OPTIMIZED_UV_NAME,
                    color_bake_image,
                    packed_bake_image,
                )

                color_bake_materials.append(color_bake_material)
                packed_bake_materials.append(packed_bake_material)
                optimized_materials.append(optimized_material)

            scene.render.engine = "CYCLES"

            for index, bake_material in enumerate(color_bake_materials):
                obj.material_slots[index].material = bake_material

            bake_materials.extend([material for material in color_bake_materials if material is not None])
            _bake_color_pass(obj, scene.uv_optimizer_bake_margin)

            packed_bake_required = any(material is not None for material in packed_bake_materials)
            if packed_bake_required:
                for index, bake_material in enumerate(packed_bake_materials):
                    obj.material_slots[index].material = bake_material if bake_material is not None else color_bake_materials[index]

                bake_materials.extend([material for material in packed_bake_materials if material is not None])
                _bake_emit_pass(obj, scene.uv_optimizer_bake_margin)

            obj.data.materials.clear()
            for optimized_material in optimized_materials:
                obj.data.materials.append(optimized_material)

            for polygon in mesh.polygons:
                if polygon.material_index >= len(optimized_materials):
                    polygon.material_index = 0

            _remove_materials(bake_materials)

            self.report(
                {"INFO"},
                f"Created optimized UVs and {target_size}x{target_size} replacement textures for {obj.name}.",
            )
            return {"FINISHED"}

        except Exception as error:
            if original_materials:
                _restore_materials(obj, original_materials)

            _remove_materials(bake_materials)

            self.report({"ERROR"}, f"Optimization failed: {error}")
            return {"CANCELLED"}

        finally:
            scene.render.engine = previous_engine

            if previous_active is not None:
                context.view_layer.objects.active = previous_active

            if obj.mode != previous_mode:
                try:
                    context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode=previous_mode)
                except RuntimeError:
                    pass


def register():
    bpy.utils.register_class(UVOPTIMIZER_OT_optimize_selected_mesh)


def unregister():
    bpy.utils.unregister_class(UVOPTIMIZER_OT_optimize_selected_mesh)
