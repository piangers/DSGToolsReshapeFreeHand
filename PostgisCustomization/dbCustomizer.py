# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2016-07-31
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
#Qt Imports
from PyQt4.Qt import QObject
#DsgTools Imports
from DsgTools.Utils.utils import Utils 
from DsgTools.Factories.DbFactory.postgisDb import PostgisDb
from DsgTools.PostgisCustomization.CustomJSONTools.customJSONValidator import CustomJSONValidator
from DsgTools.Factories.DbCustomizationFactory.dbCustomizationFactory import DbCustomizationFactory

class DbCustomizer(QObject):
    def __init__(self):
        super(DbCustomizer, self).__init__()
        self.customJSONValidator = None
        self.dbCustomizationFactory = DbCustomizationFactory()
    
    def buildCustomizationSQL(self, customJSON):
        sql = ''
        for customizationTag in customJSON.keys():
            customCreator = self.dbCustomizationFactory.createCustomization(customizationTag, customJSON[customizationTag])
            sql += customCreator.buildSql()
        return sql
    
    def buildUndoCustomizationSQL(self, customJSON):
        sql = ''
        for customizationTag in customJSON.keys():
            customCreator = self.dbCustomizationFactory.createCustomization(customizationTag, customJSON[customizationTag])
            sql += customCreator.buildUndoSql()
        return sql