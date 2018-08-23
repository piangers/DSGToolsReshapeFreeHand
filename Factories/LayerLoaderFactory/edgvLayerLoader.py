# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2016-07-16
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Philipe Borba - Cartographic Engineer @ Brazilian Army
        email                : borba.philipe@eb.mil.br
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
import os
from xml.dom.minidom import parse, parseString

# Qt imports
from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtCore import pyqtSlot, pyqtSignal, QVariant
from PyQt4.Qt import QObject

# QGIS imports
from qgis.core import QgsVectorLayer,QgsDataSourceURI, QgsMessageLog, QgsField, QGis
from qgis.utils import iface

#DsgTools imports
from DsgTools.Factories.DbFactory.abstractDb import AbstractDb
from DsgTools.Utils.utils import Utils

class EDGVLayerLoader(QObject):
    
    def __init__(self, iface, abstractDb, loadCentroids):
        """Constructor."""
        super(EDGVLayerLoader, self).__init__()
        
        self.abstractDb = abstractDb
        self.uri = QgsDataSourceURI() 
        self.iface = iface
        self.utils = Utils()
        self.logErrorDict = dict()
        self.errorLog = ''
        self.geomTypeDict = self.abstractDb.getGeomTypeDict(loadCentroids)
        self.geomDict = self.abstractDb.getGeomDict(self.geomTypeDict)
        self.correspondenceDict = {'POINT':'Point', 'MULTIPOINT':'Point', 'LINESTRING':'Line','MULTILINESTRING':'Line', 'POLYGON':'Area', 'MULTIPOLYGON':'Area'}
    
    def preLoadStep(self, inputList):
        if len(inputList) == 0:
            return [], False
        else:
            if isinstance(inputList[0], dict):
                lyrList = [i['tableName'] for i in inputList]
                return lyrList, True
            else:
                return inputList, False

    def load(self, layerList, useQml = False, uniqueLoad = False, useInheritance = False, stylePath = None, onlyWithElements = False):
        return None
    
    def getStyle(self, stylePath, className):
        if 'db:' in stylePath['style']:
            return self.abstractDb.getStyle(stylePath['style'].split(':')[-1], className)
        else:
            return self.getStyleFromFile(stylePath['style'], className)
    
    def getStyleFromFile(self, stylePath, className):
        availableStyles = os.walk(stylePath).next()[2]
        styleName = className+'.qml'
        if styleName in availableStyles:
            path = os.path.join(stylePath, styleName)
            qml = self.utils.parseStyle(path)
            return qml
        else:
            return None
    
    def prepareLoad(self):
        dbName = self.abstractDb.getDatabaseName()
        groupList =  iface.legendInterface().groups()
        if dbName in groupList:
            return groupList.index(dbName)
        else:
            parentTreeNode = iface.legendInterface().addGroup(self.abstractDb.getDatabaseName(), -1)
            return parentTreeNode

    def createMeasureColumn(self, layer):
        if layer.geometryType() == QGis.Polygon:
            layer.addExpressionField('$area', QgsField(self.tr('area_otf'), QVariant.Double))
        elif layer.geometryType() == QGis.Line:
            layer.addExpressionField('$length', QgsField(self.tr('lenght_otf'), QVariant.Double))
        return layer
    
    def getDatabaseGroup(self, groupList):
        dbName = self.abstractDb.getDatabaseName()
        if dbName in groupList:
            return groupList.index(dbName)
        else:
            return self.iface.legendInterface().addGroup(dbName, True, -1)

    def getLyrDict(self, inputList, isEdgv = True):
        """
        Builds lyrDict in order to build loading tree
        lyrList: list of layers to be loaded
        isEdgv: optional parameter to indicate when db is not edgv. If db is not edgv, layers will be grouped by schema.
        """
        lyrDict = dict()
        if isinstance(inputList, list):
            if len(inputList) > 0:
                if isinstance(inputList[0],dict):
                    for elem in inputList:
                        if elem['geomType'] == 'GEOMETRY':
                            continue
                        if self.correspondenceDict[elem['geomType']] not in lyrDict.keys():
                            lyrDict[self.correspondenceDict[elem['geomType']]] = dict()
                        if elem['cat'] not in lyrDict[self.correspondenceDict[elem['geomType']]].keys():
                            lyrDict[self.correspondenceDict[elem['geomType']]][elem['cat']] = []
                        lyrDict[self.correspondenceDict[elem['geomType']]][elem['cat']].append(elem)
                else:
                    for type in self.geomTypeDict.keys():
                        # some tables are only registered as GEOMETRY and should not be considered
                        if type == 'GEOMETRY':
                            continue
                        if self.correspondenceDict[type] not in lyrDict.keys():
                            lyrDict[self.correspondenceDict[type]] = dict()
                        for lyr in self.geomTypeDict[type]:
                            if lyr in inputList:
                                if isEdgv:
                                    cat = lyr.split('_')[0]
                                else:
                                    cat = self.abstractDb.getTableSchemaFromDb(lyr)
                                if cat not in lyrDict[self.correspondenceDict[type]].keys():
                                    lyrDict[self.correspondenceDict[type]][cat] = []
                                lyrDict[self.correspondenceDict[type]][cat].append(lyr)
                    for type in lyrDict.keys():
                        if lyrDict[type] == dict():
                            lyrDict.pop(type)
        return lyrDict

    def prepareGroups(self, groupList, parent, lyrDict):
        aux = dict()
        groupDict = dict()
        groupNodeList = lyrDict.keys()
        groupNodeList.sort(reverse=True)
        for geomNode in groupNodeList:
            groupDict[geomNode] = dict()
            aux = self.createGroup(groupList, geomNode, parent)
            catList = lyrDict[geomNode].keys()
            catList.sort()
            for catNode in catList:
                groupDict[geomNode][catNode] = self.createGroup(groupList, catNode, aux)
        return groupDict
    
    def createGroup(self, groupList, groupName, parent):
        subgroup = groupList[parent::]
        if groupName in subgroup:
            return parent+subgroup.index(groupName) #verificar
        else:
            return self.iface.legendInterface().addGroup(groupName, True, parent)
        
    def loadDomains(self, layerList, loadedLayers, domainGroup):
        domLayerDict = dict()
        qmlDict = self.abstractDb.getQmlDict(layerList)
        for lyr in layerList:
            if lyr in qmlDict.keys():
                for attr in qmlDict[lyr].keys():
                    domain = qmlDict[lyr][attr]
                    domLyr = self.checkLoaded(domain, loadedLayers)
                    if not domLyr:
                        domLyr = self.loadDomain(domain, domainGroup)
                        loadedLayers.append(domLyr)
                        domLyrName = domLyr.name()
                    if lyr not in domLayerDict.keys():
                        domLayerDict[lyr] = dict()
                    if attr not in domLayerDict[lyr].keys():
                        domLayerDict[lyr][attr] = domLyr
        return domLayerDict

    def logError(self):
        msg = ''
        for lyr in self.logErrorDict:
            msg += self.tr('Error for lyr ')+ lyr + ': ' +self.logErrorDict[lyr] + '\n'
        self.errorLog += msg

    def setDataSource(self, schema, layer, geomColumn, sql, pkColumn='id'):
        self.uri.setDataSource(schema, layer, geomColumn, sql, pkColumn)
        if sql == '':
            self.uri.disableSelectAtId(False)
        else:
            self.uri.disableSelectAtId(True)

    def setDomainsAndRestrictionsWithQml(self, vlayer):
        qmldir = ''
        try:
            qmldir, qmlType = self.abstractDb.getQml(vlayer.name())
        except Exception as e:
            QgsMessageLog.logMessage(':'.join(e.args), "DSG Tools Plugin", QgsMessageLog.CRITICAL)
            return None
        if qmlType == 'db':
            vlayer.applyNamedStyle(qmldir)
        else:
            vlayerQml = os.path.join(qmldir, vlayer.name()+'.qml')
            #treat case of qml with multi
            vlayer.loadNamedStyle(vlayerQml, False)
        return vlayer