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
import os, codecs

# Qt imports
from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtCore import pyqtSlot

# DSGTools imports

import json

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'rules_editor.ui'))

class RulesEditor(QtGui.QDialog, FORM_CLASS):
    def __init__(self, postgisDb, parent = None):
        """
        Constructor
        """
        super(RulesEditor, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        regex = QtCore.QRegExp('[0-9\*]\.\.[0-9\*]')
        validator = QtGui.QRegExpValidator(regex, self.cardinalityEdit)
        self.cardinalityEdit.setValidator(validator)
        self.cardinalityEdit.setText('1..1')
        
        self.postgisDb = postgisDb
        
        self.rulesFile = os.path.join(os.path.dirname(__file__), 'ValidationRules', 'ruleLibrary.rul')
        self.fillLayers()
        
        self.readFile()
        
    def fillLayers(self):
        """
        List classes from database
        """
        classList = self.postgisDb.listGeomClassesFromDatabase()
        classList.sort()
        self.layer1Combo.addItems(classList)
        self.layer2Combo.addItems(classList)
        
    @pyqtSlot(bool)
    def on_insertRuleButton_clicked(self):
        """
        Inserts a new rule
        """
        self.insertRow(self.layer1Combo.currentText(), \
                       str(self.necessityCombo.currentIndex())+'_'+self.necessityCombo.currentText(), \
                       str(self.predicateCombo.currentIndex())+'_'+self.predicateCombo.currentText(), \
                       self.layer2Combo.currentText(), self.cardinalityEdit.text())

    @pyqtSlot(bool)
    def on_removeRuleButton_clicked(self):
        """
        Remove a selected rule
        """
        selectedItems = self.tableWidget.selectedItems()
        rows = [self.tableWidget.row(selectedItem) for selectedItem in selectedItems]
        rows = set(rows)
        rows = list(rows)
        rows.sort()
        rows.reverse()
        for row in rows:
            self.tableWidget.removeRow(row)
        
    def insertRow(self, layer1, necessity, predicate, layer2, cardinality):
        """
        Inserts a new rule row in the rules table
        Parameters: layer1, necessity, predicate, layer2, cardinality
        """
        layer1Item = QtGui.QTableWidgetItem(layer1)
        necessityItem = QtGui.QTableWidgetItem(necessity)
        predicateItem = QtGui.QTableWidgetItem(predicate)
        layer2Item = QtGui.QTableWidgetItem(layer2)
        cardinalityItem = QtGui.QTableWidgetItem(cardinality)
        
        self.tableWidget.insertRow(self.tableWidget.rowCount())
        
        self.tableWidget.setItem(self.tableWidget.rowCount()-1, 0, layer1Item)
        self.tableWidget.setItem(self.tableWidget.rowCount()-1, 1, necessityItem)        
        self.tableWidget.setItem(self.tableWidget.rowCount()-1, 2, predicateItem)
        self.tableWidget.setItem(self.tableWidget.rowCount()-1, 3, layer2Item)        
        self.tableWidget.setItem(self.tableWidget.rowCount()-1, 4, cardinalityItem)        

    def readFile(self):
        """
        Reads the rule file
        """
        try:
            with codecs.open(self.rulesFile, 'r', encoding='utf8') as f:
                rules = [line.rstrip('\n') for line in f]
        except Exception as e:
            QtGui.QMessageBox.warning(self, self.tr('Warning!'), self.tr('Problem reading file! \n'))
            return
        
        for line in rules:
            split = line.split(',')
            layer1 = split[0]    
            necessity = split[1]
            predicate = split[2]
            layer2 = split[3]
            cardinality = split[4]
            self.insertRow(layer1, necessity, predicate, layer2, cardinality)    

    def makeRulesList(self):
        """
        Makes a rule list from the table
        """
        rules = list()
        for row in range(self.tableWidget.rowCount()):
            layer1Item = self.tableWidget.item(row, 0)
            necessityItem = self.tableWidget.item(row, 1)
            predicateItem = self.tableWidget.item(row, 2)
            layer2Item = self.tableWidget.item(row, 3)
            cardinalityItem = self.tableWidget.item(row, 4)
            
            items = list()
            items.append(layer1Item.text())
            items.append(necessityItem.text())
            items.append(predicateItem.text())
            items.append(layer2Item.text())
            items.append(cardinalityItem.text())
            
            line = ','.join(items)
            rules.append(line)
            
        return rules
    
    @pyqtSlot(int)
    def on_predicateCombo_currentIndexChanged(self, id):
        """
        Slot to update cardinality in case the predicate is ''disjoint
        """
        if self.predicateCombo.currentText() == self.tr('disjoint'):
            self.cardinalityEdit.setText('..')
            self.cardinalityEdit.setEnabled(False)
        else:
            self.cardinalityEdit.setEnabled(True)
            self.cardinalityEdit.setText('1..1')
        
    @pyqtSlot()
    def on_buttonBox_accepted(self):
        """
        Saves the rule list created
        """
        try:
            with codecs.open(self.rulesFile, 'w', encoding='utf8') as outfile:
                for line in self.makeRulesList():
                    outfile.write(line + '\n')
        except Exception as e:
            QtGui.QMessageBox.warning(self, self.tr('Warning!'), self.tr('Problem saving file! \n')+':'.join(e.args))
            return
            
        QtGui.QMessageBox.warning(self, self.tr('Warning!'), self.tr('Profile saved successfully!'))
