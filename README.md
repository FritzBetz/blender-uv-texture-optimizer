# Blender Texture Reducer

A small Blender add-on for optimising UV layouts and baking textures into a more efficient atlas.

## What it does

This plugin helps reduce wasted texture space by:

- duplicating the active UV map
- repacking UV islands into a tighter layout
- baking the original textures into new optimised atlas textures
- creating replacement materials that use the optimised UVs and baked images

The goal is to keep visual quality as high as possible while reducing unnecessary texture usage.

## Included files

- `LICENSE`
- `blender_plugin_tex_reducer/__init__.py`
- `blender_plugin_tex_reducer/optimizer.py`
- `blender_plugin_tex_reducer/properties.py`
- `blender_plugin_tex_reducer/ui.py`
- `make_ziip.py`

## Installation

1. Create a zip archive of the plugin folder.
2. In Blender, open **Edit > Preferences > Add-ons**.
3. Click **Install...** and select the zip file.
4. Enable the add-on after installation.

## Usage

1. Select a mesh object.
2. Open the **UV Optimizer** tab in the 3D View sidebar.
3. Adjust the optimisation settings if needed:
   - UV Island Margin
   - Bake Margin
   - Minimum Texture Size
   - Maximum Texture Size
4. Run **Optimize UV and Texture for Selected Mesh**.

## Notes

- Save your Blender file before baking production assets.
- The add-on currently works on the selected mesh object.
- Results depend on the original UVs, materials, and texture setup.

## Licence

See the `LICENSE` file for licence details.
