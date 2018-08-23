# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2015-03-29
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
from DsgTools.Factories.ThreadFactory.postgisDbThread import PostgisDbThread
from DsgTools.Factories.ThreadFactory.dpiThread import DpiThread
from DsgTools.Factories.ThreadFactory.inventoryThread import InventoryThread

class ThreadFactory:
    def makeProcess(self, name):
        """
        Returns the specific thread to be initiated
        :param name:
        :return:
        """
        if name == 'pgdb':
            return PostgisDbThread()
        elif name == 'dpi':
            return DpiThread()
        elif name == 'inventory':
            return InventoryThread()
        else:
            return None
