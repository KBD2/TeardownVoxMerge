import math
from typing import Self

"""
Tools for working with MagicaVoxel Vox files.
NOT COMPATIBLE WITH EVERY VERSION!
Doesn't currently support animated vox files.
Makes assumptions about the file, e.g. there being only one group node chunk per file,
as MV doesn't seem to fully use these features (yet), and it makes building the scene
tree *significantly* easier.
Also - slightly scuffed code, going for fast MVP here

Vox format references:
- https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt
- https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox-extension.txt
"""

MAT_BOUNDARIES = [
    (1, 8), # Glass
    (9, 24), # Grass
    (25, 40), # Dirt
    (41, 56), # Rock
    (57, 72), # Wood
    (73, 88), # Concrete
    (89, 104), # Brick
    (105, 120), # Plaster
    (121, 136), # Weak metal
    (137, 152), # Heavy metal
    (153, 168), # Plastic
    (169, 224), # Reserved
    (225, 240), # Unphysical
    (241, 255) # Reserved
]

def rgbDifference(a: int, b: int):
    colourA = [
                (a) & 0xff,
                (a >> 8) & 0xff,
                (a >> 16) & 0xff,
                (a >> 24)
    ]
    colourB = [
                (b) & 0xff,
                (b >> 8) & 0xff,
                (b >> 16) & 0xff,
                (b >> 24)
    ]
    return math.sqrt(math.pow(colourA[0] - colourB[0], 2) + math.pow(colourA[1] - colourB[1], 2) + math.pow(colourA[2] - colourB[2], 2) + math.pow(colourA[3] - colourB[3], 2))

class VoxChunk:
    def __init__(this, parent=None):
        this.parent = parent

    def read(this, data: bytes, cursor: int) -> int:

        numChildren = 0

        this.children: list[VoxChunk] = []

        this.name = data[cursor : cursor + 4].decode()
        this.contentSize = int(data[cursor + 7 : cursor + 3 : -1].hex(), 16)
        this.childrenContentSize = int(data[cursor + 11 : cursor + 7 : -1].hex(), 16)

        cursor = cursor + 12

        this._data = data[cursor : cursor + this.contentSize]

        cursor = cursor + this.contentSize

        endIndex = cursor + this.childrenContentSize

        while cursor < endIndex:
            chunkName = data[cursor : cursor + 4].decode()
            if chunkName == 'SIZE':
                this.children.append(SizeChunk(this))
            elif chunkName == 'nTRN':
                this.children.append(TransformNodeChunk(this))
            elif chunkName == 'nSHP':
                this.children.append(ShapeNodeChunk(this))
            elif chunkName == 'RGBA':
                this.children.append(PaletteChunk(this))
            elif chunkName == 'nGRP':
                this.children.append(GroupNodeChunk(this))
            elif chunkName == 'MATL':
                this.children.append(MaterialChunk(this))
            elif chunkName == 'rCAM':
                this.children.append(RenderCameraChunk(this))
            elif chunkName == 'rOBJ':
                this.children.append(RenderObjectsChunk(this))
            elif chunkName == 'NOTE':
                this.children.append(NoteChunk(this))
            elif chunkName == 'XYZI':
                this.children.append(ShapeIndexesChunk(this))
            elif chunkName == 'LAYR':
                this.children.append(LayerChunk(this))
            else:
                this.children.append(VoxChunk(this))
            cursor, childChildren = this.children[-1].read(data, cursor)
            this.children[-1].parseChunkData()
            numChildren += childChildren + 1

        return cursor, numChildren
    
    def filterChildren(this, name: str) -> list[Self]:
        ret = []
        for child in this.children:
            if child.name == name:
                ret.append(child)

        return ret
    
    def parseChunkData(this):
        pass

    def parseInt(this, cursor: int = 0) -> (int, int):
        # 4 bytes, little-endian
        if cursor == 0:
            return int(this._data[3::-1].hex(), 16), cursor + 4
        return int(this._data[cursor + 3 : cursor - 1 : -1].hex(), 16), cursor + 4
    
    def parseString(this, cursor: int) -> (str, int):
        # 4 bytes for string length then n bytes for unterminated string
        size, cursor = this.parseInt(cursor)
        return this._data[cursor : cursor + size].decode(), cursor + size
    
    def parseDict(this, cursor: int) -> (dict, int):
        # 4 bytes for number of entries then n string key-value pairs
        ret = {}
        numEntries, cursor = this.parseInt(cursor)
        for _ in range(numEntries):
            key, cursor = this.parseString(cursor)
            value, cursor = this.parseString(cursor)
            ret[key] = value
        return ret, cursor
    
    def buildInt(this, var: int) -> bytes:
        if var >= 0:
            return var.to_bytes(4, 'little')
        else:
            return var.to_bytes(4, 'little', signed=True)
    
    def buildString(this, var: str) -> bytes:
        return len(var).to_bytes(4, 'little') + var.encode('utf-8')
    
    def buildDict(this, var: dict) -> bytes:
        ret = this.buildInt(len(var.keys()))
        for k, v, in var.items():
            ret += this.buildString(k) + this.buildString(v)
        return ret
    
    # Right now, only the main chunk has child chunks, and we manually write that anyway
    # So we only ever need to treat chunks we serialise as having no children
    def serialiseShallow(this) -> bytes:
        ret = bytes()
        ret += this.name[:].encode('utf-8')

        ret += this.contentSize.to_bytes(4, 'little')
        ret += bytearray([0, 0, 0, 0])

        ret += this._data

        return ret
    
class SizeChunk(VoxChunk):
    def parseChunkData(this):
        this.sizeX, _ = this.parseInt(0x0)
        this.sizeY, _ = this.parseInt(0x4)
        this.sizeZ, _ = this.parseInt(0x8)

class TransformNodeChunk(VoxChunk):
    def parseChunkData(this):
        this.nodeId, cursor = this.parseInt()
        this.attributes, cursor = this.parseDict(cursor)
        this.childNodeId, cursor = this.parseInt(cursor)
        this.layerId, cursor = this.parseInt(cursor + 4)
        this.transform, cursor = this.parseDict(cursor + 4)

    def serialiseShallow(this) -> bytes:
        content = this.buildInt(this.nodeId)
        content += this.buildDict(this.attributes)
        content += this.buildInt(this.childNodeId)
        content += this.buildInt(-1)
        content += this.buildInt(this.layerId)
        content += this.buildInt(1)
        content += this.buildDict(this.transform)

        ret = bytes("nTRN", 'utf-8')
        ret += len(content).to_bytes(4, 'little')
        ret += bytearray([0, 0, 0, 0])

        ret += content

        return ret

# NOT THE VOXEL DATA CHUNK! That's ShapeIndexesChunk - this contains scene graph data.
class ShapeNodeChunk(VoxChunk):
    def parseChunkData(this):
        this.nodeId, cursor = this.parseInt(0x0)
        this.attributes, cursor = this.parseDict(cursor)
        _, cursor = this.parseInt(cursor)
        this.modelId, cursor = this.parseInt(cursor)
        this.modelAttributes, cursor = this.parseDict(cursor)
    
    def serialiseShallow(this) -> bytes:

        content = this.buildInt(this.nodeId)
        content += this.buildDict(this.attributes)
        content += this.buildInt(1)
        content += this.buildInt(this.modelId)
        content += this.buildDict(this.modelAttributes)

        ret = bytes("nSHP", 'utf-8')
        ret += len(content).to_bytes(4, 'little')
        ret += bytearray([0, 0, 0, 0])

        ret += content

        return ret

class PaletteChunk(VoxChunk):
    def parseChunkData(this):
        this.palette = []
        cursor = 0
        for cursor in range(0, len(this._data), 4):
            this.palette.append(this.parseInt(cursor)[0])
    
    def serialiseShallow(this) -> bytes:
        ret = bytes("RGBA", 'utf-8')
        ret += this.buildInt(1024) + this.buildInt(0)
        for colour in this.palette:
            ret += this.buildInt(colour)
            
        return ret

class ShapeIndexesChunk(VoxChunk):
    def parseChunkData(this):
        this.numVoxels, cursor = this.parseInt()
        this.indices = []
        for _ in range(this.numVoxels):
            packed, cursor = this.parseInt(cursor)
            this.indices.append([
                (packed) & 0xff,
                (packed >> 8) & 0xff,
                (packed >> 16) & 0xff,
                (packed >> 24)
            ])
    
    def serialiseShallow(this) -> bytes:
        ret = bytes("XYZI", 'utf-8')

        content = this.buildInt(this.numVoxels)

        for index in this.indices:
            content += bytearray([index[0], index[1], index[2], index[3]])

        ret += this.buildInt(len(content))
        ret += this.buildInt(0)
        ret += content
        
        return ret

class RenderCameraChunk(VoxChunk):
    def parseChunkData(this):
        pass

class RenderObjectsChunk(VoxChunk):
    def parseChunkData(this):
        pass

class LayerChunk(VoxChunk):
    def parseChunkData(this):
        pass

class MaterialChunk(VoxChunk):
    def parseChunkData(this):
        pass

class GroupNodeChunk(VoxChunk):
    def parseChunkData(this):
        this.nodeId, cursor = this.parseInt()
        this.attributes, cursor = this.parseDict(cursor)
        this.numChildren, cursor = this.parseInt(cursor)
        this.childIDs = []
        for _ in range(this.numChildren):
            childID, cursor = this.parseInt(cursor)
            this.childIDs.append(childID)

        this._data = []

    def serialiseShallow(this) -> bytes:
        content = this.buildInt(this.nodeId)
        content += this.buildDict(this.attributes)
        content += this.buildInt(len(this.childIDs))
        for id in this.childIDs:
            content += this.buildInt(id)
        
        ret = bytes("nGRP", 'utf-8')
        
        ret += len(content).to_bytes(4, 'little')
        ret += bytearray([0, 0, 0, 0])

        ret += content

        return ret

class NoteChunk(VoxChunk):
    def parseChunkData(this):
        pass

class VoxShape:
    def __init__(this, transform: TransformNodeChunk, size: SizeChunk, shape: ShapeNodeChunk, indexes: ShapeIndexesChunk, palette: PaletteChunk):
        this.transformChunk = transform
        this.sizeChunk = size
        this.shapeChunk = shape
        this.indexesChunk = indexes
        this.paletteChunk = palette
    
class VoxFile:
    def __init__(this, fileName: str):
        print("VOX PARSER:", fileName)
        with open(fileName, 'rb') as file:
            data = file.read()
            identifier = data[:4]
            assert identifier == b'VOX ' # From here on we assume the file is legit

            version = data[7:3:-1]

            print("File version:", int(version.hex(), 16))

            cursor: int = 8
            this.mainChunk = VoxChunk()
            cursor, numChildren = this.mainChunk.read(data, cursor)

            print("Read", numChildren, "chunks\n")

            # Yeah this is probably bad practise but I just wanted to get the script working

            this.sizeChunks = lambda: this.mainChunk.filterChildren("SIZE")
            this.indexChunks = lambda: this.mainChunk.filterChildren("XYZI")

            this.groupNodeChunk = this.mainChunk.filterChildren("nGRP")[0]

            this.transformNodeChunks = lambda: this.mainChunk.filterChildren("nTRN")
            this.shapeNodeChunks = lambda: this.mainChunk.filterChildren("nSHP")

            this.renderCameraChunks = lambda: this.mainChunk.filterChildren("rCAM")
            this.renderObjectChunks = lambda: this.mainChunk.filterChildren("rOBJ")
            this.materialChunks = lambda: this.mainChunk.filterChildren("MATL")
            this.noteChunks = lambda: this.mainChunk.filterChildren("NOTE")
            this.layerChunks = lambda: this.mainChunk.filterChildren("LAYR")

            this.paletteChunk = this.mainChunk.filterChildren("RGBA")[0]

            this.models = zip(this.sizeChunks(), this.indexChunks(), this.shapeNodeChunks())

            this.shapes: list[VoxShape] = []

            for model in this.models:
                transformId = model[2].nodeId - 1
                for chunk in this.transformNodeChunks():
                    if chunk.nodeId == transformId:
                        this.shapes.append(VoxShape(chunk, model[0], model[2], model[1], this.paletteChunk))

    """NOTE:
        A colour index in the palette is equal to the shape index - 1
    """
    def mergeShape(this, shape: VoxShape, dontPreserve=False):
        inUse = [False] * 255
        for chunk in this.indexChunks():
            for index in chunk.indices:
                inUse[index[3] - 1] = True

        # Create a set of the colours we need to remap 
        toMerge = set()
        for index in shape.indexesChunk.indices:
            toMerge.add(index[3] - 1)
        
        # Try to remap each colour to a free spot in the appropriate section, and find the closest colour if we can't
        mappings = []
        for colour in toMerge:
            section = list(filter(lambda x: colour >= x[0] - 1 and colour <= x[1] - 1, MAT_BOUNDARIES))[0]
            found = False
            if not dontPreserve:
                bounds = range(section[0], section[1])
            else:
                bounds = range(1, 255)
            for index in bounds:
                if not inUse[index - 1]:
                    found = True
                    mappings.append((colour, index - 1))
                    this.paletteChunk.palette[index - 1] = shape.paletteChunk.palette[colour]
                    inUse[index - 1] = True
                    break
            if not found:
                # Find the closest colour using the Euclidian distance formula and create a mapping for it.
                # We don't copy the palette over here as we assume the main vox file has priority.
                minDifference = 1e99
                minIndex = 0
                for index in bounds:
                    diff = rgbDifference(this.paletteChunk.palette[index - 1], shape.paletteChunk.palette[colour])
                    if diff < minDifference:
                        minDifference = diff
                        minIndex = index
                mappings.append((colour, minIndex - 1))
                inUse[index - 1] = True

        # Go through the shape indices and apply the appropriate mapping
        for index in shape.indexesChunk.indices:
            for mapping in mappings:
                if index[3] - 1 == mapping[0]:
                    index[3] = mapping[1] + 1
                    break

        
        highestId = this.shapeNodeChunks()[-1].nodeId

        # Adding a new shape is currently as easy as adding a transform and shape node, with IDs one and two
        # higher than the last shape node.
        shape.transformChunk.nodeId = highestId + 1
        shape.transformChunk.childNodeId = highestId + 2
        shape.shapeChunk.nodeId = highestId + 2
        shape.shapeChunk.modelId = len(this.mainChunk.filterChildren("nSHP"))

        # We can then just append all the chunks to the main chunk's children, as they'll be written in the
        # appropriate order anyway.
        this.mainChunk.children.append(shape.transformChunk)
        this.mainChunk.children.append(shape.shapeChunk)
        this.mainChunk.children.append(shape.sizeChunk)
        this.mainChunk.children.append(shape.indexesChunk)

        this.groupNodeChunk.childIDs.append(highestId + 1)

    def merge(this, vox: Self, dontPreserve=False):
        for shape in vox.shapes:
            this.mergeShape(shape, dontPreserve)
    
    def write(this, fileName: str):
        mainChunkData = bytes("MAIN", 'utf-8') + bytearray((0).to_bytes(4, 'little'))

        contentChunksData = bytes()

        # Size and index chunks are written interlaced
        for s, i in zip(this.sizeChunks(), this.indexChunks()):
            contentChunksData += s.serialiseShallow()
            contentChunksData += i.serialiseShallow()

        # We then write the first transform node and its child group node
        contentChunksData += this.transformNodeChunks()[0].serialiseShallow()
        contentChunksData += this.groupNodeChunk.serialiseShallow()

        # Then the shape transforms and their node data are written interlaced
        for t, s in zip(this.transformNodeChunks()[1:], this.shapeNodeChunks()):
            contentChunksData += t.serialiseShallow()
            contentChunksData += s.serialiseShallow()

        # Then we dump everything else in
        for chunk in this.materialChunks():
            contentChunksData += chunk.serialiseShallow()
        for chunk in this.layerChunks():
            contentChunksData += chunk.serialiseShallow()
        for chunk in this.renderObjectChunks():
            contentChunksData += chunk.serialiseShallow()
        for chunk in this.renderCameraChunks():
            contentChunksData += chunk.serialiseShallow()
        for chunk in this.noteChunks():
            contentChunksData += chunk.serialiseShallow()
            
        contentChunksData += this.paletteChunk.serialiseShallow()

        # We can now add the child content size to the main chunk
        mainChunkData += bytearray(len(contentChunksData).to_bytes(4, 'little'))

        with open(fileName, "wb") as file:
            file.write(b'VOX ')
            file.write((200).to_bytes(4, 'little'))
            file.write(mainChunkData)
            file.write(contentChunksData)