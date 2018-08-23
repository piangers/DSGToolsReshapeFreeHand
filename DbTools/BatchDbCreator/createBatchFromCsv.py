# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2016-02-18
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
import json

from qgis.core import QgsMessageLog

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal, Qt
from PyQt4.QtGui import QMessageBox, QFileDialog, QApplication, QCursor
from fileinput import filename
from DsgTools.Utils.utils import Utils
from DsgTools.Factories.DbCreatorFactory.dbCreatorFactory import DbCreatorFactory

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'createBatchFromCsv.ui'))

class CreateBatchFromCsv(QtGui.QWizardPage, FORM_CLASS):
    coverageChanged = pyqtSignal()
    def __init__(self, parent=None):
        """Constructor."""
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.databaseParameterWidget.setDbNameVisible(False)
        self.customFileSelector.setCaption(self.tr('Select a Comma Separated Values File'))
        self.customFileSelector.setFilter(self.tr('Comma Separated Values File (*.csv)'))
        self.customFileSelector.setType('single')
        self.customFileSelector.setTitle(self.tr('CSV File'))
        self.tabDbSelectorWidget.tabWidget.currentChanged.connect(self.changeTemplateInterface)
        self.tabDbSelectorWidget.serverWidget.serverAbstractDbLoaded.connect(self.databaseParameterWidget.setServerDb)
        self.databaseParameterWidget.comboBoxPostgis.parent = self
    
    def getParameters(self):
        #Get outputDir, outputList, refSys
        parameterDict = dict()
        parameterDict['prefix'] = None
        parameterDict['sufix'] = None
        parameterDict['srid'] = self.databaseParameterWidget.mQgsProjectionSelectionWidget.crs().authid().split(':')[-1]
        parameterDict['version'] = self.databaseParameterWidget.getVersion()
        parameterDict['nonDefaultTemplate'] = self.databaseParameterWidget.getTemplateName()
        if self.databaseParameterWidget.prefixLineEdit.text() <> '':
            parameterDict['prefix'] = self.databaseParameterWidget.prefixLineEdit.text()
        if self.databaseParameterWidget.sufixLineEdit.text() <> '':
            parameterDict['sufix'] = self.databaseParameterWidget.sufixLineEdit.text()
        parameterDict['miList'] = self.getMiListFromCSV() 
        parameterDict['driverName'] = self.tabDbSelectorWidget.getType()
        parameterDict['factoryParam'] = self.tabDbSelectorWidget.getFactoryCreationParam()
        parameterDict['templateInfo'] = self.databaseParameterWidget.getTemplateParameters()
        return parameterDict
    
    def getMiListFromCSV(self):
        f = open(self.customFileSelector.fileNameList,'r')
        miList = [i.replace('\n','').strip() for i in f.readlines()]
        miList = [i for i in miList if i <> '']
        return miList

    def validatePage(self):
        #insert validation messages
        validatedDbParams = self.databaseParameterWidget.validate()
        if not validatedDbParams:
            return False
        validated = self.tabDbSelectorWidget.validate()
        if not validated:
            return False
        parameterDict = self.getParameters()
        dbDict, errorDict = self.createDatabases(parameterDict)
        creationMsg = ''
        if len(dbDict.keys()) > 0:
            creationMsg += self.tr('Database(s) {0} created successfully.').format(', '.join(dbDict.keys()))
        errorFrameMsg = ''
        errorMsg = ''
        if len(errorDict.keys()) > 0:
            frameList = []
            errorList = []
            for key in errorDict.keys():
                if self.tr('Invalid inomen parameter!') in errorDict[key]:
                    frameList.append(key)
                else:
                    errorList.append(key)
                QgsMessageLog.logMessage(self.tr('Error on {0}: ').format(key)+errorDict[key], "DSG Tools Plugin", QgsMessageLog.CRITICAL)
            if len(frameList) > 0:
                errorFrameMsg += self.tr('Frame was not created on the following databases: {0}').format(', '.join(frameList))
            if len(errorList) > 0:
                errorMsg += self.tr('Some errors occurred while trying to create database(s) {0}').format(', '.join(errorList))
        logMsg = ''
        if errorFrameMsg != '' or errorMsg != '':
            logMsg += self.tr('Check log for more details.')
        msg = [i for i in (creationMsg, errorFrameMsg, errorMsg, logMsg) if i != '']
        QMessageBox.warning(self, self.tr('Info!'), self.tr('Process finished.')+'\n'+'\n'.join(msg))
        return True
    
    def createDatabases(self, parameterDict):
        dbCreator = DbCreatorFactory().createDbCreatorFactory(parameterDict['driverName'], parameterDict['factoryParam'], parentWidget = self)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        dbDict, errorDict =dbCreator.createDbFromMIList(parameterDict['miList'], parameterDict['srid'], prefix = parameterDict['prefix'], sufix = parameterDict['sufix'], createFrame = True, paramDict = parameterDict['templateInfo'])
        QApplication.restoreOverrideCursor()
        return dbDict, errorDict
    
    def changeTemplateInterface(self):
        if self.tabDbSelectorWidget.tabWidget.currentIndex() == 1:
            self.databaseParameterWidget.changeInterfaceState(True, hideInterface = True)
        else:
            self.databaseParameterWidget.changeInterfaceState(True, hideInterface = False)
