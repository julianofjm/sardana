#!/usr/bin/env python

##############################################################################
##
## This file is part of Sardana
##
## http://www.tango-controls.org/static/sardana/latest/doc/html/index.html
##
## Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
## 
## Sardana is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## 
## Sardana is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
## 
## You should have received a copy of the GNU Lesser General Public License
## along with Sardana.  If not, see <http://www.gnu.org/licenses/>.
##
##############################################################################

"""This module is part of the Python Pool libray. It defines the base classes
for"""

__all__ = [ "PoolBaseGroup", "PoolGroupElement" ]

__docformat__ = 'restructuredtext'

from sardana import State
from pooldefs import ElementType, TYPE_PHYSICAL_ELEMENTS
from poolelement import PoolBaseElement
from poolcontainer import PoolContainer


class PoolBaseGroup(PoolContainer):

    def __init__(self, **kwargs):
        user_elem_ids = kwargs.pop('user_elements')
        PoolContainer.__init__(self)
        
        self._user_elements = []
        self._physical_elements = {}
        
        pool = self._get_pool()
        for id in user_elem_ids:
            self.add_user_element(pool.get_element(id=id))

    def _get_pool(self):
        raise NotImplementedError

    def _calculate_states(self):
        user_elements = self.get_user_elements()
        fault, alarm, on, moving = [], [], [], []
        status = []
        for elem in user_elements:
            s = elem.inspect_state()
            if s == State.Moving:
                moving.append(elem)
                status.append(elem.name + " is in MOVING")
            elif s == State.On: 
                on.append(elem)
                status.append(elem.name + " is in ON")
            elif s == State.Fault:
                fault.append(elem)
                status.append(elem.name + " is in FAULT")
            elif s == State.Alarm:
                alarm.append(elem)
                status.append(elem.name + " is in ALARM")
        state = State.On
        if fault:
            state = State.Fault
        elif alarm:
            state = State.Alarm
        elif moving:
            state = State.Moving
        self._state_statistics = { State.On : on, State.Fault : fault,
                                   State.Alarm : alarm, State.Moving : moving }
        return state, status
    
    def on_element_changed(self, evt_src, evt_type, evt_value):
        pass

    def get_action_cache(self):
        return self._action_cache
    
    def set_action_cache(self, action_cache):
        physical_elements = self.get_physical_elements()
        if self._action_cache is not None:
            for ctrl_physical_elements in physical_elements.values():
                for physical_element in ctrl_physical_elements:
                    action_cache.remove_element(physical_element)
            
        self._action_cache = action_cache
        
        for ctrl, ctrl_physical_elements in physical_elements.items():
            for physical_element in ctrl_physical_elements:
                action_cache.add_element(physical_element)
    
    def get_user_elements(self):
        return self._user_elements
    
    def get_physical_elements(self):
        return self._physical_elements
    
    def add_user_element(self, element, index=None):
        if element in self._user_elements:
            raise Exception("Group already contains %s" % element.name)
        if index is None:
            index = len(self._user_elements)
        self._user_elements.insert(index, element)
        self.add_element(element)

        physical_elements = self._find_physical_elements(element,
                                physical_elements=self._physical_elements)
        if self._action_cache is not None:
            for ctrl, ctrl_physical_elements in physical_elements.items():
                for physical_element in ctrl_physical_elements:
                    self._action_cache.add_element(physical_element)
        
        element.add_listener(self.on_element_changed)
        return index
    
    def _find_physical_elements(self, element, physical_elements=None):
        elem_type = element.get_type()
        if physical_elements is None:
            physical_elements = {}
        if elem_type in TYPE_PHYSICAL_ELEMENTS:
            ctrl = element.controller
            own_elements = physical_elements.get(ctrl)
            if own_elements is None:
                physical_elements[ctrl] = own_elements = set()
            own_elements.add(element)
        else:
            for data in element.get_physical_elements():
                for ctrl, elements in data.items():
                    own_elements = physical_elements.get(ctrl)
                    if own_elements is None:
                        physical_elements[ctrl] = own_elements = set()
                    own_elements.update(elements)
        return physical_elements
    
    def remove_user_element(self, element):
        try:
            idx = self._user_elements.index(element)
        except ValueError:
            raise Exception("Group doesn't contain %s" % element.name)
        element.remove_listener(self.on_element_changed)
        del self._user_elements[idx]
        self.remove_element(element)


class PoolGroupElement(PoolBaseElement, PoolBaseGroup):
    
    def __init__(self, **kwargs):
        user_elements = kwargs.pop('user_elements')
        PoolBaseElement.__init__(self, **kwargs)
        PoolBaseGroup.__init__(self, user_elements=user_elements)
    
    def _get_pool(self):
        return self.pool