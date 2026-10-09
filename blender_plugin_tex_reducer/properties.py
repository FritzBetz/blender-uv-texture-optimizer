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

from bpy.props import FloatProperty, IntProperty
from bpy.types import Scene


def register():
    Scene.uv_optimizer_pack_margin = FloatProperty(
        name="UV Island Margin",
        description="Padding between repacked UV islands",
        default=0.001,
        min=0.0,
        max=0.1,
        precision=4,
    )

    Scene.uv_optimizer_bake_margin = IntProperty(
        name="Bake Margin",
        description="Pixel margin used when baking the optimized texture",
        default=2,
        min=0,
        max=128,
    )

    Scene.uv_optimizer_min_texture_size = IntProperty(
        name="Minimum Texture Size",
        description="Minimum generated texture size",
        default=256,
        min=64,
        max=16384,
    )

    Scene.uv_optimizer_max_texture_size = IntProperty(
        name="Maximum Texture Size",
        description="Maximum generated texture size",
        default=4096,
        min=64,
        max=16384,
    )


def unregister():
    if hasattr(Scene, "uv_optimizer_pack_margin"):
        del Scene.uv_optimizer_pack_margin
    if hasattr(Scene, "uv_optimizer_bake_margin"):
        del Scene.uv_optimizer_bake_margin
    if hasattr(Scene, "uv_optimizer_min_texture_size"):
        del Scene.uv_optimizer_min_texture_size
    if hasattr(Scene, "uv_optimizer_max_texture_size"):
        del Scene.uv_optimizer_max_texture_size
