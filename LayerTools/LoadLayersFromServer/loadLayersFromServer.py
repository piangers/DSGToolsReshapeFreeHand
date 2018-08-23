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
        email                : borba@dsg.eb.mil.br
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
from os.path import expanduser

from qgis.core import QgsMessageLog

# Qt imports
from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSlot, Qt, QSettings
from PyQt4.QtGui import QListWidgetItem, QMessageBox, QMenu, QApplication, QCursor, QFileDialog, QProgressBar
from PyQt4.QtSql import QSqlDatabase,QSqlQuery

# DSGTools imports
from DsgTools.Utils.utils import Utils
from DsgTools.Factories.SqlFactory.sqlGeneratorFactory import SqlGeneratorFactory
from DsgTools.ServerTools.viewServers import ViewServers
from DsgTools.Factories.DbFactory.dbFactory import DbFactory
from DsgTools.Factories.LayerLoaderFactory.layerLoaderFactory import LayerLoaderFactory
from DsgTools.ServerTools.createView import CreateView
from DsgTools.ServerTools.manageDBAuxiliarStructure import ManageDBAuxiliarStructure
from DsgTools.ServerTools.selectStyles import SelectStyles
from DsgTools.CustomWidgets.progressWidget import ProgressWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'loadLayersFromServer.ui'))

class LoadLayersFromServer(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(self.__class__, self).__init__(parent)
        self.iface = iface
        self.utils = Utils()
        self.setupUi(self)
        self.layerFactory = LayerLoaderFactory()
        self.customServerConnectionWidget.postgisCustomSelector.setTitle(self.tr('Select Databases'))
        self.customServerConnectionWidget.spatialiteCustomSelector.setTitle(self.tr('Selected Spatialites'))
        self.layersCustomSelector.setTitle(self.tr('Select layers to be loaded'))
        self.customServerConnectionWidget.dbDictChanged.connect(self.updateLayersFromDbs)
        self.customServerConnectionWidget.resetAll.connect(self.resetInterface)
        self.customServerConnectionWidget.styleChanged.connect(self.populateStyleCombo)
        self.headerList = [self.tr('Category'), self.tr('Layer Name'), self.tr('Geometry\nColumn'), self.tr('Geometry\nType'), self.tr('Layer\nType')]
        self.layersCustomSelector.setHeaders(self.headerList)
        self.customServerConnectionWidget.postgisEdgvComboFilter.currentIndexChanged.connect(self.layersCustomSelector.setInitialState)
        self.customServerConnectionWidget.spatialiteEdgvComboFilter.currentIndexChanged.connect(self.layersCustomSelector.setInitialState)
        self.customServerConnectionWidget.serverConnectionTab.currentChanged.connect(self.layersCustomSelector.setInitialState)
        self.lyrDict = dict()
    
    def resetInterface(self):
        """
        Sets the initial state again
        """
        self.layersCustomSelector.clearAll()
        self.styleComboBox.clear()
        #TODO: refresh optional parameters
        self.checkBoxOnlyWithElements.setCheckState(0)
        self.onlyParentsCheckBox.setCheckState(0)

    @pyqtSlot()
    def on_buttonBox_rejected(self):
        """
        Closes the dialog
        """
        self.close()
    
    def updateLayersFromDbs(self, type, dbList, showViews = False):
        """
        
        """
        errorDict = dict()
        if type == 'added':
            progress = ProgressWidget(1, len(dbList), self.tr('Reading selected databases... '), parent=self)
            progress.initBar()
            for dbName in dbList:
                try:
                    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                    geomList = self.customServerConnectionWidget.selectedDbsDict[dbName].getGeomColumnTupleList(showViews = showViews)
                    for tableSchema, tableName, geom, geomType, tableType in geomList:
                        if self.customServerConnectionWidget.edgvType == 'Non_EDGV':
                            lyrName = tableName
                            cat = tableSchema
                        else:
                            lyrName = '_'.join(tableName.split('_')[1::])
                            cat = tableName.split('_')[0]
                        key = ','.join([cat, lyrName, geom, geomType, tableType])
                        if key not in self.lyrDict.keys():
                            self.lyrDict[key] = dict()
                        self.lyrDict[key][dbName] = {'tableSchema':tableSchema, 'tableName':tableName, 'geom':geom, 'geomType':geomType, 'tableType':tableType, 'lyrName':lyrName, 'cat':cat}
                except Exception as e:
                    errorDict[dbName] = ':'.join(e.args)
                    QApplication.restoreOverrideCursor()
                progress.step()
                QApplication.restoreOverrideCursor()
                
        elif type == 'removed':
            for key in self.lyrDict.keys():
                for db in self.lyrDict[key].keys():
                    if db in dbList:
                        self.lyrDict[key].pop(db)
                if self.lyrDict[key] == dict():
                    self.lyrDict.pop(key)
        interfaceDictList = []
        for key in self.lyrDict.keys():
            cat, lyrName, geom, geomType, tableType = key.split(',')
            interfaceDictList.append({self.tr('Category'):cat, self.tr('Layer Name'):lyrName, self.tr('Geometry\nColumn'):geom, self.tr('Geometry\nType'):geomType, self.tr('Layer\nType'):tableType})
        self.layersCustomSelector.setInitialState(interfaceDictList,unique = True)
            
    @pyqtSlot()
    def on_buttonBox_accepted(self):
        """
        Loads the selected classes/categories
        """
        #1- filter classes if categories is checked and build list.
        selectedKeys = self.layersCustomSelector.getSelectedNodes()
        if len(selectedKeys) == 0:
            QMessageBox.information(self, self.tr('Error!'), self.tr('Select at least one layer to be loaded!'))
            return

        #2- get parameters
        withElements = self.checkBoxOnlyWithElements.isChecked()
        selectedStyle = None
        if self.customServerConnectionWidget.edgvType == 'Non_EDGV':
            isEdgv = False
        else:
            isEdgv = True
        if self.styleComboBox.currentIndex() != 0:
            selectedStyle = self.customServerConnectionWidget.stylesDict[self.styleComboBox.currentText()]
        uniqueLoad = self.uniqueLoadCheckBox.isChecked()
        onlyParents = self.onlyParentsCheckBox.isChecked()
        #3- Build factory dict
        factoryDict = dict()
        dbList = self.customServerConnectionWidget.selectedDbsDict.keys()
        for dbName in dbList:
            factoryDict[dbName] = self.layerFactory.makeLoader(self.iface, self.customServerConnectionWidget.selectedDbsDict[dbName])
        #4- load for each db
        exceptionDict = dict()
        progress = ProgressWidget(1, len(dbList), self.tr('Loading layers from selected databases... '), parent=self)
        for dbName in factoryDict.keys():
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            try:
                selectedClasses = []
                for i in selectedKeys:
                    if i in self.lyrDict.keys():
                        if dbName in self.lyrDict[i].keys():
                            selectedClasses.append(self.lyrDict[i][dbName])
                factoryDict[dbName].load(selectedClasses, uniqueLoad=uniqueLoad, onlyWithElements=withElements, stylePath=selectedStyle, useInheritance=onlyParents, isEdgv=isEdgv, parent=self)
                progress.step()
            except Exception as e:
                exceptionDict[dbName] = ':'.join(e.args)
                QApplication.restoreOverrideCursor()
                progress.step()
            QApplication.restoreOverrideCursor()
            if factoryDict[dbName].errorLog != '':
                if dbName in exceptionDict.keys():
                    exceptionDict[dbName] += '\n'+factoryDict[dbName].errorLog
                else:
                    exceptionDict[dbName] = factoryDict[dbName].errorLog
        QApplication.restoreOverrideCursor()
        self.logInternalError(exceptionDict)
        self.close()
    
    def logInternalError(self, exceptionDict):
        """
        Logs internal errors during the load process in QGIS' log
        """
        msg = ''
        errorDbList = exceptionDict.keys()
        if len(errorDbList) > 0:
            msg += self.tr('\nDatabases with error:')
            msg += ', '.join(errorDbList)
            msg += self.tr('\nError messages for each database were output in qgis log.')
            for errorDb in errorDbList:
                QgsMessageLog.logMessage(self.tr('Error for database ') + errorDb + ': ' +exceptionDict[errorDb], "DSG Tools Plugin", QgsMessageLog.CRITICAL)
        return msg 

    def populateStyleCombo(self, styleDict):
        """
        Loads styles saved in the database
        """
        self.styleComboBox.clear()
        styleList = styleDict.keys()
        numberOfStyles = len(styleList)
        if numberOfStyles > 0:
            self.styleComboBox.addItem(self.tr('Select Style'))
            for i in range(numberOfStyles):
                self.styleComboBox.addItem(styleList[i])
        else:
            self.styleComboBox.addItem(self.tr('No available styles'))