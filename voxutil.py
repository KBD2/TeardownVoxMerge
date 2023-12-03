from typing import Self

"""
Tools for reading MagicaVoxel Vox files.
NOT COMPATIBLE WITH EVERY VERSION!
Doesn't currently support animated vox files.
Also - slightly scuffed code, going for fast MVP here
"""


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
        if cursor == 0:
            return int(this._data[3::-1].hex(), 16), cursor + 4
        return int(this._data[cursor + 3 : cursor - 1 : -1].hex(), 16), cursor + 4
    
    def parseString(this, cursor: int) -> (str, int):
        size, cursor = this.parseInt(cursor)
        return this._data[cursor : cursor + size].decode(), cursor + size
    
    def parseDict(this, cursor: int) -> (dict, int):
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
    
    def serialise(this) -> bytes:
        childData = bytes()
        #for child in this.children:
        #    childData += child.serialise()

        ret = bytes()
        ret += this.name[:].encode('utf-8')

        ret += this.contentSize.to_bytes(4, 'little')
        ret += len(childData).to_bytes(4, 'little')

        ret += this._data

        ret += childData

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

    def serialise(this) -> bytes:
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

class ShapeNodeChunk(VoxChunk):
    def parseChunkData(this):
        this.nodeId, cursor = this.parseInt(0x0)
        this.attributes, cursor = this.parseDict(cursor)
        _, cursor = this.parseInt(cursor)
        this.modelId, cursor = this.parseInt(cursor)
        this.modelAttributes, cursor = this.parseDict(cursor)
    
    def serialise(this) -> bytes:

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
            this.palette.append(int(this._data[cursor : cursor + 3].hex(), 16))

class ShapeIndexesChunk(VoxChunk):
    def parseChunkData(this):
        pass

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

    def serialise(this) -> bytes:
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
    def __init__(this, transform: TransformNodeChunk, size: SizeChunk, shape: ShapeNodeChunk, indexes: ShapeIndexesChunk):
        this.transformChunk = transform
        this.sizeChunk = size
        this.shapeChunk = shape
        this.indexesChunk = indexes
    
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
                        this.shapes.append(VoxShape(chunk, model[0], model[2], model[1]))

    def mergeShape(this, shape: VoxShape):
        highestId = this.shapeNodeChunks()[-1].nodeId

        shape.transformChunk.nodeId = highestId + 1
        shape.transformChunk.childNodeId = highestId + 2
        shape.shapeChunk.nodeId = highestId + 2
        shape.shapeChunk.modelId = len(this.mainChunk.filterChildren("nSHP"))

        this.mainChunk.children.append(shape.transformChunk)
        this.mainChunk.children.append(shape.shapeChunk)
        this.mainChunk.children.append(shape.sizeChunk)
        this.mainChunk.children.append(shape.indexesChunk)

        this.groupNodeChunk.childIDs.append(highestId + 1)

    def merge(this, vox: Self):
        for shape in vox.shapes:
            this.mergeShape(shape)
    
    def write(this, fileName: str):
        mainChunkData = bytes("MAIN", 'utf-8') + bytearray((0).to_bytes(4, 'little'))

        contentChunksData = bytes()

        for s, i in zip(this.sizeChunks(), this.indexChunks()):
            contentChunksData += s.serialise()
            contentChunksData += i.serialise()

        contentChunksData += this.transformNodeChunks()[0].serialise()
        contentChunksData += this.groupNodeChunk.serialise()

        for t, s in zip(this.transformNodeChunks()[1:], this.shapeNodeChunks()):
            contentChunksData += t.serialise()
            contentChunksData += s.serialise()

        for chunk in this.materialChunks():
            contentChunksData += chunk.serialise()
        for chunk in this.layerChunks():
            contentChunksData += chunk.serialise()
        for chunk in this.renderObjectChunks():
            contentChunksData += chunk.serialise()
        for chunk in this.renderCameraChunks():
            contentChunksData += chunk.serialise()
        for chunk in this.noteChunks():
            contentChunksData += chunk.serialise()
            
        contentChunksData += this.paletteChunk.serialise()

        mainChunkData += bytearray(len(contentChunksData).to_bytes(4, 'little'))

        with open(fileName, "wb") as file:
            file.write(b'VOX ')
            file.write((200).to_bytes(4, 'little'))
            file.write(mainChunkData)
            file.write(contentChunksData)