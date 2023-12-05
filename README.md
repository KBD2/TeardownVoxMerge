## TEARDOWN VOX MERGE TOOL
This script allows you to merge multiple vox files whilst keeping the materials intact for each of them.  
The tool attempts to copy colours and remap incoming shapes to preserve the shape's colours, but if there aren't any free indexes available it will find the closest colour for each colour's material section and remap to that.

### Usage:
`python voxmerge.py [-nopreserve] path_to_main_vox [path_to_merging_vox ...]`

`-nopreserve` will disable the material preservation, in case you're doing something like making a tool and don't care about that.

The tool will output `output.vox` containing the merged vox files. The tool will preserve the non-shape data in the main vox file, but any non-shape-related data in the merging files will not be kept.

#### References for the .vox file format:
- [Base format](https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt)
- [Extensions](https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox-extension.txt)  

Note: Doesn't currently support vox files that use animation frames.
