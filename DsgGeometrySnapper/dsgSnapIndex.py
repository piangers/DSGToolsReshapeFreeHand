# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2017-03-18
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Luiz Andrade - Cartographic Engineer @ Brazilian Army
        email                : luiz.claudio@dsg.eb.mil.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import sys, math

from qgis.core import QgsAbstractGeometryV2, QgsVertexId, QgsPoint, QgsPointV2, QgsVector, QgsCurvePolygonV2, QgsCircularStringV2, QgsMultiPolygonV2, QgsPolygonV2

from DsgTools.DsgGeometrySnapper.raytracer import Raytracer
from DsgTools.DsgGeometrySnapper.coordIdx import CoordIdx
from DsgTools.DsgGeometrySnapper.snapItem import SnapItem
from DsgTools.DsgGeometrySnapper.pointSnapItem import PointSnapItem
from DsgTools.DsgGeometrySnapper.segmentSnapItem import SegmentSnapItem
from DsgTools.DsgGeometrySnapper.gridRow import GridRow

class DsgSnapIndex:
    SnapPoint, SnapSegment = range(2)

    def __init__(self, origin, cellSize):
        """
        Constructor
        :param origin: QgsPointV2
        :param cellSize: double
        """
        self.origin = origin
        self.cellSize = cellSize
        self.rowsStartIdx = 0
        self.coordIdxs = []
        self.gridRows = []

    def __del__(self):
        """
        Destructor
        :return: list of CoordIdx
        """
        for coordIdx in self.coordIdxs:
            del coordIdx

    def getCell(self, col, row):
        """
        Gets a cell
        :param col: int
        :param row: int
        :return:
        """
        if row < self.rowsStartIdx or row >= self.rowsStartIdx + len(self.gridRows):
            return None        
        else:        
            return self.gridRows[row - self.rowsStartIdx].getCell(col)

    def getCreateCell(self, col, row):
        """
        Gets create cell
        :param col: int
        :param row: int
        :return:
        """
        if row < self.rowsStartIdx:
            for i in xrange(row, self.rowsStartIdx):
                self.gridRows.insert(0, GridRow())
            self.rowsStartIdx = row
            return self.gridRows[0].getCreateCell(col)
        elif row >= self.rowsStartIdx + len(self.gridRows):
            for  i in xrange(self.rowsStartIdx + len(self.gridRows), row + 1):
                self.gridRows.append(GridRow())
            return self.gridRows[-1].getCreateCell(col)
        else:
            return self.gridRows[row - self.rowsStartIdx].getCreateCell(col)

    def addPoint(self, idx):
        """
        Adds a point into the index
        :param idx: CoordIdx
        :return:
        """
        p = idx.point()
        col = int(math.floor((p.x() - self.origin.x()) / self.cellSize))
        row = int(math.floor((p.y() - self.origin.y()) / self.cellSize))
        self.getCreateCell(col, row).append(PointSnapItem(idx))

    def addSegment(self, idxFrom, idxTo):
        """
        Adds a segmento into the index
        :param idxFrom: CoordIdx
        :param idxTo: CoordIdx
        :return:
        """
        pFrom = idxFrom.point()
        pTo = idxTo.point()
        # Raytrace along the grid, get touched cells
        x0 = (pFrom.x() - self.origin.x()) / self.cellSize
        y0 = (pFrom.y() - self.origin.y()) / self.cellSize
        x1 = (pTo.x() - self.origin.x()) / self.cellSize
        y1 = (pTo.y() - self.origin.y()) / self.cellSize

        rt = Raytracer(x0, y0, x1, y1)
        while rt.isValid():
            rt.next()
            self.getCreateCell(rt.curCol(), rt.curRow()).append(SegmentSnapItem(idxFrom, idxTo))

    def addGeometry(self, geom):
        """
        Add geometry into the index
        :param geom:QgsAbstractGeometryV2
        :return:
        """
        for iPart in xrange(geom.partCount()):
            for iRing in xrange(geom.ringCount(iPart)):
                nVerts = geom.vertexCount(iPart, iRing)
                if isinstance(geom, QgsMultiPolygonV2):
                    nVerts -= 1
                elif isinstance(geom, QgsPolygonV2):
                    nVerts -= 1
                elif isinstance(geom, QgsCircularStringV2):
                    nVerts -= 1
                for iVert in xrange(nVerts):
                    idx = CoordIdx( geom, QgsVertexId(iPart, iRing, iVert, QgsVertexId.SegmentVertex))
                    idx1 = CoordIdx( geom, QgsVertexId(iPart, iRing, iVert + 1, QgsVertexId.SegmentVertex))
                    self.coordIdxs.append(idx)
                    self.coordIdxs.append(idx1)
                    self.addPoint(idx)
                    if iVert < nVerts - 1:
                        self.addSegment(idx, idx1)

    def getClosestSnapToPoint(self, p, q):
        """
        Get closest snap point
        :param p: QgsPointV2
        :param q: QgsPointV2
        :return:
        """
        # Look for intersections on segment from the target point to the point opposite to the point reference point
        p2 = QgsPointV2( 2 * q.x() - p.x(), 2 * q.y() - p.y() )
        
        # Raytrace along the grid, get touched cells
        x0 = (p.x() - self.origin.x()) / self.cellSize
        y0 = (p.y() - self.origin.y()) / self.cellSize
        x1 = (p2.x() - self.origin.x()) / self.cellSize
        y1 = (p2.y() - self.origin.y()) / self.cellSize
        
        rt = Raytracer(x0, y0, x1, y1)
        dMin = sys.float_info.max
        pMin = p
        while rt.isValid():
            rt.next()
            cell = self.getCell(rt.curCol(), rt.curRow())
            if not cell:
                continue
            for item in cell:
                if item.snapType == DsgSnapIndex.SnapSegment:
                    if isinstance(item, SegmentSnapItem):
                        inter = item.getIntersection(p, p2)
                        if inter:
                            qF = QgsPoint(q.toQPointF())
                            interF = QgsPoint(inter.toQPointF())
                            dist = qF.sqrDist(interF)
                            if dist < dMin:
                                dMin = dist
                                pMin = inter
        return pMin

    def getSnapItem(self, pos, tol):
        """
        Gets snap item
        :param pos: QgsPointV2
        :param tol: double
        :param pSnapPoint: PointSnapItem
        :param pSnapSegment: SegmentSnapItem
        :return:
        """
        colStart = int(math.floor((pos.x() - tol - self.origin.x()) / self.cellSize))
        rowStart = int(math.floor((pos.y() - tol - self.origin.y()) / self.cellSize))
        colEnd = int(math.floor((pos.x() + tol - self.origin.x()) / self.cellSize))
        rowEnd = int(math.floor((pos.y() + tol - self.origin.y()) / self.cellSize))

        rowStart = max(rowStart, self.rowsStartIdx)
        rowEnd = min(rowEnd, self.rowsStartIdx + len(self.gridRows) - 1)

        items = []
        for row in xrange(rowStart, rowEnd+1):
            items.append(self.gridRows[row - self.rowsStartIdx].getSnapItems(colStart, colEnd))    

        minDistSegment = sys.float_info.max
        minDistPoint = sys.float_info.max
        snapSegment = None
        snapPoint = None
        
        # QgsPoint used to calculate squared distance
        posF = QgsPoint(pos.toQPointF())
        for cellList in items:
            for cell in cellList:
                for item in cell:
                    if item.snapType == DsgSnapIndex.SnapPoint:
                        dist = QgsPoint(item.getSnapPoint(pos).toQPointF()).sqrDist(posF)
                        if dist < minDistPoint:
                            minDistPoint = dist
                            snapPoint = item
                    elif item.snapType == DsgSnapIndex.SnapSegment:
                        pProj = item.getProjection(pos)
                        if not pProj:
                            continue
                        pProjF = QgsPoint(pProj.toQPointF())
                        dist = pProjF.sqrDist(posF)
                        if dist < minDistSegment:
                            minDistSegment = dist
                            snapSegment = item

        snapPoint = snapPoint if minDistPoint < tol * tol else None
        snapSegment = snapSegment if minDistSegment < tol * tol else None
        return snapPoint, snapSegment


