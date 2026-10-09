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

import bpy
from bpy.types import Panel


class UVOPTIMIZER_PT_sidebar(Panel):
    bl_label = "UV Texture Optimizer"
    bl_idname = "UVOPTIMIZER_PT_sidebar"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UV Optimizer"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object

        if obj is None or obj.type != "MESH":
            layout.label(text="Select a mesh object.")
            return

        layout.label(text="Selected Mesh:")
        layout.label(text=obj.name, icon="MESH_DATA")
        layout.separator()

        layout.prop(scene, "uv_optimizer_pack_margin")
        layout.prop(scene, "uv_optimizer_bake_margin")
        layout.prop(scene, "uv_optimizer_min_texture_size")
        layout.prop(scene, "uv_optimizer_max_texture_size")

        layout.separator()
        layout.operator(
            "uv_optimizer.optimize_selected_mesh",
            text="Optimize UV and Texture for Selected Mesh",
            icon="UV",
        )


def register():
    bpy.utils.register_class(UVOPTIMIZER_PT_sidebar)


def unregister():
    bpy.utils.unregister_class(UVOPTIMIZER_PT_sidebar)
