# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2016-08-25
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
import os, sqlite3
import json

from qgis.core import QgsMessageLog
from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSlot, pyqtSignal, Qt
from PyQt4.QtGui import QMessageBox, QFileDialog, QApplication, QCursor
from DsgTools.Utils.utils import Utils
from DsgTools.CustomWidgets.progressWidget import ProgressWidget
from DsgTools.CustomWidgets.tabDbSelectorWidget import TabDbSelectorWidget
from DsgTools.Factories.DbCreatorFactory.dbCreatorFactory import DbCreatorFactory

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'createBatchIncrementing.ui'))

class CreateBatchIncrementing(QtGui.QWizardPage, FORM_CLASS):
    parametersSet = pyqtSignal(dict)
    def __init__(self, parent=None):
        """Constructor."""
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.databaseParameterWidget.setDbNameVisible(False)
        self.tabDbSelectorWidget.serverWidget.serverAbstractDbLoaded.connect(self.databaseParameterWidget.setServerDb)
        self.databaseParameterWidget.comboBoxPostgis.parent = self
        self.databaseParameterWidget.useFrame = False
        self.databaseParameterWidget.setDbNameVisible(True)
    
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
        parameterDict['dbBaseName'] = self.databaseParameterWidget.dbNameLineEdit.text()
        parameterDict['driverName'] = self.tabDbSelectorWidget.getType()
        parameterDict['factoryParam'] = self.tabDbSelectorWidget.getFactoryCreationParam()
        parameterDict['numberOfDatabases'] = self.spinBox.value()
        parameterDict['templateInfo'] = self.databaseParameterWidget.getTemplateParameters()
        return parameterDict

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
        errorMsg = ''
        if len(errorDict.keys()) > 0:
            frameList = []
            errorList = []
            for key in errorDict.keys():
                errorList.append(key)
                QgsMessageLog.logMessage(self.tr('Error on {0}: ').format(key)+errorDict[key], "DSG Tools Plugin", QgsMessageLog.CRITICAL)
            if len(errorList) > 0:
                errorMsg += self.tr('Some errors occurred while trying to create database(s) {0}').format(', '.join(errorList))
        logMsg = ''
        if errorMsg != '':
            logMsg += self.tr('Check log for more details.')
        msg = [i for i in (creationMsg, errorMsg, logMsg) if i != '']
        QMessageBox.warning(self, self.tr('Info!'), self.tr('Process finished.')+'\n'+'\n'.join(msg))
        return True
    
    def createDatabases(self, parameterDict):
        dbCreator = DbCreatorFactory().createDbCreatorFactory(parameterDict['driverName'], parameterDict['factoryParam'], parentWidget = self)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        dbDict, errorDict = dbCreator.createDbWithAutoIncrementingName(parameterDict['dbBaseName'], parameterDict['srid'], parameterDict['numberOfDatabases'], prefix = parameterDict['prefix'], sufix = parameterDict['sufix'], paramDict = parameterDict['templateInfo'])
        QApplication.restoreOverrideCursor()
        return dbDict, errorDict
