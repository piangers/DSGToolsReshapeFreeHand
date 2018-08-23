# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                             -------------------
        begin                : 2015-09-10
        git sha              : $Format:%H$
        copyright            : (C) 2014 by Luiz Andrade - Cartographic Engineer @ Brazilian Army
        email                : luiz.claudio@dsg.eb.mil.br
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

from PyQt4 import QtGui

from qgis.core import QgsMessageLog, QgsDataSourceURI

from DsgTools.ValidationTools.ValidationProcesses.validationProcess import ValidationProcess
from DsgTools.CustomWidgets.progressWidget import ProgressWidget

class SpatialRuleProcess(ValidationProcess):
    #this relates the predicate with the PostGIS ST functions
    predicates = {0:'ST_Equals',
                  1:'ST_Disjoint',
                  2:'ST_Intersects',
                  3:'ST_Touches',
                  4:'ST_Crosses',
                  5:'ST_Within',
                  6:'ST_Overlaps',
                  7:'ST_Contains',
                  8:'ST_Covers',
                  9:'ST_CoveredBy'}
    
    #we must check is this is violated to raise flags, hence the opposite idea
    necessity = {0:'\'f\'',
                 1:'\'t\''}
    
    def __init__(self, postgisDb, iface, instantiating=False):
        """
        Constructor
        """
        super(self.__class__,self).__init__(postgisDb, iface, instantiating)
        
        self.rulesFile = os.path.join(os.path.dirname(__file__), '..', 'ValidationRules', 'ruleLibrary.rul')
        self.processAlias = self.tr('Spatial Rule Checker')
        
    def getRules(self):
        """
        Get a list of tuples (rules) using the configuration file
        """
        try:
            with open(self.rulesFile, 'r') as f:
                rules = [line.rstrip('\n') for line in f]
        except Exception as e:
            QtGui.QMessageBox.warning(self, self.tr('Warning!'), self.tr('Problem reading file!'))
            return
        
        ret = list()
        for line in rules:
            split = line.split(',')
            layer1 = split[0]    
            necessity = self.necessity[int(split[1].split('_')[0])]
            predicate = self.predicates[int(split[2].split('_')[0])]
            layer2 = split[3]
            cardinality = split[4]
            if cardinality:
                min_card = cardinality.split('..')[0]
                max_card = cardinality.split('..')[1]
            else:
                min_card = max_card = None         
            rule = split[1]+' '+split[2]
            ret.append((layer1, necessity, predicate, layer2, min_card, max_card, rule))
            
        return ret

    def execute(self):
        """
        Reimplementation of the execute method from the parent class
        """
        QgsMessageLog.logMessage(self.tr('Starting ')+self.getName()+self.tr(' Process.'), "DSG Tools Plugin", QgsMessageLog.CRITICAL)
        self.startTimeCount()
        try:
            self.setStatus(self.tr('Running'), 3) #now I'm running!
            self.abstractDb.deleteProcessFlags(self.getName())
            
            rules = self.getRules()
            for rule in rules:
                # preparation
                localProgress = ProgressWidget(0, 1, self.tr('Preparing execution for ') + rule[0], parent=self.iface.mapCanvas())
                localProgress.step()
                class_a, lyrA, aKeyColumn = self.prepareExecution(rule[0])
                class_b, lyrB, bKeyColumn = self.prepareExecution(rule[3])
                # getting keyColumn because we want to be generic
                aGeomColumn = self.getGeometryColumnFromLayer(lyrA)
                bGeomColumn = self.getGeometryColumnFromLayer(lyrB)
                localProgress.step()

                #running the process in the temp table
                localProgress = ProgressWidget(0, 1, self.tr('Running process on ') + class_a, parent=self.iface.mapCanvas())
                localProgress.step()
                invalidGeomRecordList = self.abstractDb.testSpatialRule(class_a, rule[1], rule[2], class_b, rule[4], rule[5], rule[6], aKeyColumn, bKeyColumn, aGeomColumn, bGeomColumn)
                localProgress.step()
                                
                # dropping temp table
                self.abstractDb.dropTempTable(class_a)
                self.abstractDb.dropTempTable(class_b)

                if len(invalidGeomRecordList) > 0:
                    numberOfInvGeom = self.addFlag(invalidGeomRecordList)
                    for tuple in invalidGeomRecordList:
                        self.addClassesToBeDisplayedList(tuple[0])
                    msg = str(numberOfInvGeom) + self.tr(' features are invalid. Check flags.')
                    self.setStatus(msg, 4) #Finished with flags
                else:
                    msg = self.tr('All features are valid.')
                    self.setStatus(msg, 1) #Finished
            return 1             
        except Exception as e:
            QgsMessageLog.logMessage(':'.join(e.args), "DSG Tools Plugin", QgsMessageLog.CRITICAL)
            self.finishedWithError()
            return 0

