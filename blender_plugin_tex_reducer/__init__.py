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

bl_info = {
    "name": "Selected Mesh UV Texture Optimizer",
    "description": "Adds a View3D Sidebar tool that repacks UVs and bakes reduced textures for the selected mesh.",
    "author": "Aaron Powell",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > UV Optimizer",
    "warning": "Save your file before baking production assets.",
    "wiki_url": "http://my.wiki.url",
    "tracker_url": "http://my.bugtracker.url",
    "support": "COMMUNITY",
    "category": "UV"
}

if "bpy" in locals():
    import importlib
    importlib.reload(properties)
    importlib.reload(optimizer)
    importlib.reload(ui)
else:
    from . import properties
    from . import optimizer
    from . import ui


def register():
    properties.register()
    optimizer.register()
    ui.register()


def unregister():
    ui.unregister()
    optimizer.unregister()
    properties.unregister()


if __name__ == '__main__':
    register()
