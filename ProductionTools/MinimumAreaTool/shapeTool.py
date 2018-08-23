# -*- coding: utf-8 -*-
"""
/***************************************************************************
ShapeTool
                                 A QGIS plugin
Builds a temp rubberband with a given size and shape.
                             -------------------
        begin                : 2016-08-02
        git sha              : $Format:%H$
        copyright            : (C) 2016 by  Jossan Costa - Surveying Technician @ Brazilian Army
                                            Felipe Diniz - Cartographic Engineer @ Brazilian Army
        email                : jossan.costa@eb.mil.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.gui import QgsRubberBand, QgsMapTool
from qgis.core import QgsPoint, QGis
from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtGui import QColor, QCursor, QWidget
from PyQt4.QtCore import pyqtSignal, QObject, Qt as Qt2, QPoint
from math import sqrt, cos, sin, pi, atan2

class ShapeTool(QgsMapTool):
    #signal emitted when the mouse is clicked. This indicates that the tool finished its job
    toolFinished = pyqtSignal()
    def __init__(self, canvas, geometryType, param, type, color = QColor( 254, 178, 76, 63 )):
        """
        Constructor
        """
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.active = False
        self.geometryType = geometryType
        self.param=param
        self.type=type       
        self.cursor=None
        self.rubberBand = QgsRubberBand(self.canvas, QGis.Polygon)     
        self.setColor(color)
        self.reset()
        self.rotAngle = 0
        self.currentCentroid = None
        self.rotate = False
    
    def setColor(self, mFillColor):
        """
        Adjusting the color to create the rubber band
        """
    
        self.rubberBand.setColor(mFillColor)
        self.rubberBand.setWidth(1)
    
    def reset(self):
        """
        Resetting the rubber band
        """
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        try:
            self.rubberBand.reset(QGis.Polygon)
        except:
            pass

    def rotateRect(self, centroid, e):
        """
        Calculates the angle for the rotation.
        """
        item_position = self.canvas.mapToGlobal(e.pos())
        c = self.toCanvasCoordinates(centroid)
        c = self.canvas.mapToGlobal(c)
        rotAngle = pi - atan2(item_position.y() - c.y(), item_position.x() - c.x())
        return rotAngle

    def canvasPressEvent(self, e):
        """
        When the canvas is pressed the tool finishes its job
        """
        # enforce mouse restoring if clicked right after rotation 
        QtGui.QApplication.restoreOverrideCursor()
        self.canvas.unsetMapTool(self)
        self.toolFinished.emit()

    def canvasMoveEvent(self, e):
        """
        Deals with mouse move event to update the rubber band position in the canvas
        """
        ctrlIsHeld = QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier
        if e.button() != None and not ctrlIsHeld:
            if self.rotate:
                # change rotate status
                self.rotate = False
            QtGui.QApplication.restoreOverrideCursor()
            self.endPoint = self.toMapCoordinates( e.pos() )
        elif e.button() != None and ctrlIsHeld \
            and self.geometryType == self.tr(u"Square"):
            # calculate angle between mouse and last rubberband centroid before holding control
            self.rotAngle = self.rotateRect(self.currentCentroid, e)
            if not self.rotate:
                # only override mouse if it is not overriden already
                QtGui.QApplication.setOverrideCursor(QCursor(Qt2.BlankCursor))
                self.rotate = True
        if self.geometryType == self.tr(u"Circle"):
                self.showCircle(self.endPoint)
        elif self.geometryType == self.tr(u"Square"):
            self.showRect(self.endPoint, sqrt(self.param)/2, self.rotAngle)
    
    def showCircle(self, startPoint):
        """
        Draws a circle in the canvas
        """
        nPoints = 50
        x = startPoint.x()
        y = startPoint.y()
        if self.type == self.tr('distance'):
            r = self.param
            self.rubberBand.reset(QGis.Polygon)
            for itheta in range(nPoints+1):
                theta = itheta*(2.0*pi/nPoints)
                self.rubberBand.addPoint(QgsPoint(x+r*cos(theta), y+r*sin(theta)))
            self.rubberBand.show()
        else:
            r = sqrt(self.param/pi)
            self.rubberBand.reset(QGis.Polygon)
            for itheta in range(nPoints+1):
                theta = itheta*(2.0*pi/nPoints)
                self.rubberBand.addPoint(QgsPoint(x+r*cos(theta), y+r*sin(theta)))
            self.rubberBand.show()

    def showRect(self, startPoint, param, rotAngle=0):
        """
        Draws a rectangle in the canvas
        """  
        self.rubberBand.reset(QGis.Polygon)
        x = startPoint.x() # center point x
        y = startPoint.y() # center point y
        # rotation angle is always applied in reference to center point
        # to avoid unnecessary calculations
        c = cos(rotAngle)
        s = sin(rotAngle)
        # translating coordinate system to rubberband centroid
        point1 = QgsPoint((- param), (- param))
        point2 = QgsPoint((- param), ( param))
        point3 = QgsPoint((param), ( param))
        point4 = QgsPoint((param), (- param))
        # rotating and moving to original coord. sys.
        point1_ = QgsPoint(point1.x()*c - point1.y()*s + x, point1.y()*c + point1.x()*s + y)
        point2_ = QgsPoint(point2.x()*c - point2.y()*s + x, point2.y()*c + point2.x()*s + y)
        point3_ = QgsPoint(point3.x()*c - point3.y()*s + x, point3.y()*c + point3.x()*s + y)
        point4_ = QgsPoint(point4.x()*c - point4.y()*s + x, point4.y()*c + point4.x()*s + y)
        self.rubberBand.addPoint(point1_, False)
        self.rubberBand.addPoint(point2_, False)
        self.rubberBand.addPoint(point3_, False)
        self.rubberBand.addPoint(point4_, True)
        self.rubberBand.show()
        self.currentCentroid = startPoint
        
    def deactivate(self):
        """
        Deactivates the tool and hides the rubber band
        """
        self.rubberBand.hide()
        QgsMapTool.deactivate(self)
        # restore mouse in case tool is disabled right after rotation
        QtGui.QApplication.restoreOverrideCursor()
        
    def activate(self):
        """
        Activates the tool
        """
        QgsMapTool.activate(self)
    
    def reproject(self, geom, canvasCrs):
        """
        Reprojects geom from the canvas crs to the reference crs
        geom: geometry to be reprojected
        canvasCrs: canvas crs (from crs)
        """
        destCrs = self.reference.crs()
        if canvasCrs.authid() != destCrs.authid():
            coordinateTransformer = QgsCoordinateTransform(canvasCrs, destCrs)
            geom.transform(coordinateTransformer)