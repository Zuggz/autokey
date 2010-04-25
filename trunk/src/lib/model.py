# -*- coding: utf-8 -*-

# Copyright (C) 2008 Chris Dekter

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import re
from configmanager import *
from iomediator import Key, NAVIGATION_KEYS, KEY_SPLIT_RE
from scripting import Store

DEFAULT_WORDCHAR_REGEX = '[\w]'

def get_value_or_default(jsonData, key, default):
    if key in jsonData:
        return jsonData[key]
    else:
        return default

class AbstractAbbreviation:
    """
    Abstract class encapsulating the common functionality of an abbreviation
    """

    def __init__(self):
        self.abbreviation = None
        self.backspace = True
        self.ignoreCase = False
        self.immediate = False
        self.triggerInside = False
        self.set_word_chars(DEFAULT_WORDCHAR_REGEX)

    def get_serializable(self):
        d = {
            "abbreviation": self.abbreviation,
            "backspace": self.backspace,
            "ignoreCase": self.ignoreCase,
            "immediate": self.immediate,
            "triggerInside": self.triggerInside,
            "wordChars": self.get_word_chars()
            }
        return d

    def load_from_serialized(self, data):
        self.abbreviation = data["abbreviation"]
        self.backspace = data["backspace"]
        self.ignoreCase = data["ignoreCase"]
        self.immediate = data["immediate"]
        self.triggerInside = data["triggerInside"]
        self.set_word_chars(data["wordChars"])
        
    def copy_abbreviation(self, abbr):
        self.abbreviation = abbr.abbreviation
        self.backspace = abbr.backspace
        self.ignoreCase = abbr.ignoreCase
        self.immediate = abbr.immediate
        self.triggerInside = abbr.triggerInside
        self.set_word_chars(abbr.get_word_chars())
                        
    def set_word_chars(self, regex):
        self.wordChars = re.compile(regex, re.UNICODE)
        
    def get_word_chars(self):
        return self.wordChars.pattern
        
    def set_abbreviation(self, abbr):
        self.abbreviation = abbr

    def get_abbreviation(self):
        if TriggerMode.ABBREVIATION not in self.modes:
            return ""
        else:
            return self.abbreviation
        
    def _should_trigger_abbreviation(self, buffer):
        """
        Checks whether, based on the settings for the abbreviation and the given input,
        the abbreviation should trigger.
        
        @param buffer Input buffer to be checked (as string)
        """
        stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
        
        if len(typedAbbr) > 0:            
            # Check trigger character condition
            if not self.immediate:
                # If not immediate expansion, check last character
                if len(stringAfter) == 1:
                    # Have a character after abbr
                    if self.wordChars.match(stringAfter):
                        # last character(s) is a word char, can't send expansion
                        return False
                    elif len(stringAfter) > 1:
                        # Abbr not at/near end of buffer any more, can't send
                        return False
                else:
                    # Nothing after abbr yet, can't expand yet
                    return False
            
            else:
                # immediate option enabled, check abbr is at end of buffer
                if len(stringAfter) > 0:
                    return False
                
            # Check chars ahead of abbr
            # length of stringBefore should always be > 0
            if len(stringBefore) > 0:
                if self.wordChars.match(stringBefore[-1]):
                    # last char before is a word char
                    if not self.triggerInside:
                        # can't trigger when inside a word
                        return False
            
            return True
        
        return False
    
    def _partition_input(self, currentString):
        """
        Partition the input into text before, text after, and typed abbreviation (if it exists)
        """
        if self.ignoreCase:
            matchString = currentString.lower()
            stringBefore, typedAbbr, stringAfter = matchString.rpartition(self.abbreviation)
            abbrStart = len(stringBefore)
            abbrEnd = abbrStart + len(typedAbbr)
            typedAbbr = currentString[abbrStart:abbrEnd]
        else:
            stringBefore, typedAbbr, stringAfter = currentString.rpartition(self.abbreviation)     
            
        return (stringBefore, typedAbbr, stringAfter)
    
            
class AbstractWindowFilter:
    
    def __init__(self):
        self.windowTitleRegex = None

    def get_serializable(self):
        if self.windowTitleRegex is not None:
            return self.windowTitleRegex.pattern
        else:
            return None

    def load_from_serialized(self, pattern):
        self.set_window_titles(pattern)
        
    def copy_window_filter(self, filter):
        self.windowTitleRegex = filter.windowTitleRegex
    
    def set_window_titles(self, regex):
        if regex is not None:
            self.windowTitleRegex = re.compile(regex, re.UNICODE)
        else:
            self.windowTitleRegex = regex
            
    def uses_default_filter(self):
        return self.windowTitleRegex is None
    
    def get_filter_regex(self):
        if self.windowTitleRegex is not None:
            return self.windowTitleRegex.pattern
        else:
            return ""

    def _should_trigger_window_title(self, windowTitle):
        if self.windowTitleRegex is not None:
            return self.windowTitleRegex.match(windowTitle)
        else:
            return True        
            
            
class AbstractHotkey(AbstractWindowFilter):
    
    def __init__(self):
        self.modifiers = []
        self.hotKey = None

    def get_serializable(self):
        d = {
            "modifiers": self.modifiers,
            "hotKey": self.hotKey
            }
        return d

    def load_from_serialized(self, data):
        self.set_hotkey(data["modifiers"], data["hotKey"])
        
    def copy_hotkey(self, theHotkey):
        [self.modifiers.append(modifier) for modifier in theHotkey.modifiers]
        self.hotKey = theHotkey.hotKey
        
    def set_hotkey(self, modifiers, key):
        modifiers.sort()
        self.modifiers = modifiers
        self.hotKey = key
        
    def check_hotkey(self, modifiers, key, windowTitle):
        if self.hotKey is not None and self._should_trigger_window_title(windowTitle):
            return (self.modifiers == modifiers) and (self.hotKey == key)
        else:
            return False

    def get_hotkey_string(self, key=None, modifiers=None):
        if key is None and modifiers is None:
            if TriggerMode.HOTKEY not in self.modes:
                return ""
                
            key = self.hotKey
            modifiers = self.modifiers
            
        ret = ""

        for modifier in modifiers:
            ret += modifier
            ret += "+"

        if key == ' ':
            ret += "<space>"
        else:
            ret += key

        return ret
    
        
class Folder(AbstractAbbreviation, AbstractHotkey, AbstractWindowFilter):
    """
    Manages a collection of subfolders/phrases/scripts, which may be associated 
    with an abbreviation or hotkey.
    """
    
    def __init__(self, title, showInTrayMenu=False):
        AbstractAbbreviation.__init__(self)
        AbstractHotkey.__init__(self)
        AbstractWindowFilter.__init__(self)
        self.title = title
        self.folders = []
        self.items = []
        self.modes = []
        self.usageCount = 0
        self.showInTrayMenu = showInTrayMenu
        self.parent = None

    def get_serializable(self):
        d = {
            "type": "folder",
            "title": self.title,
            "folders": [folder.get_serializable() for folder in self.folders],
            "items": [item.get_serializable() for item in self.items],
            "modes": self.modes,
            "usageCount": self.usageCount,
            "showInTrayMenu": self.showInTrayMenu,
            "abbreviation": AbstractAbbreviation.get_serializable(self),
            "hotkey": AbstractHotkey.get_serializable(self),
            "filter": AbstractWindowFilter.get_serializable(self)
            }
        return d

    def load_from_serialized(self, data, parent):
        self.title = data["title"]
        self.folders = []
        for folderData in data["folders"]:
            f = Folder("")
            f.load_from_serialized(folderData, self)
            self.folders.append(f)
            
        self.items = []
        for itemData in data["items"]:
            if itemData["type"] == "phrase":
                i = Phrase("", "")
            else:
                i = Script("", "")

            i.load_from_serialized(itemData, self)
            self.items.append(i)
        
        self.modes = data["modes"]
        self.usageCount = data["usageCount"]
        self.showInTrayMenu = data["showInTrayMenu"]
        self.parent = parent

        AbstractAbbreviation.load_from_serialized(self, data["abbreviation"])
        AbstractHotkey.load_from_serialized(self, data["hotkey"])
        AbstractWindowFilter.load_from_serialized(self, data["filter"])
        
    def get_tuple(self):
        return ("folder", self.title, self.get_abbreviation(), self.get_hotkey_string(), self)
    
    def set_modes(self, modes):
        self.modes = modes
        
    def add_folder(self, folder):
        folder.parent = self
        #self.folders[folder.title] = folder
        self.folders.append(folder)
        
    def remove_folder(self, folder):
        #del self.folders[folder.title]
        self.folders.remove(folder)
        
    def add_item(self, item):
        """
        Add a new script or phrase to the folder.
        """
        item.parent = self
        #self.phrases[phrase.description] = phrase
        self.items.append(item)
        
    def remove_item(self, item):
        """
        Removes the given phrase or script from the folder.
        """
        #del self.phrases[phrase.description]
        self.items.remove(item)
        
    def set_modes(self, modes):
        self.modes = modes
        
    def check_input(self, buffer, windowName):
        if TriggerMode.ABBREVIATION in self.modes:
            return self._should_trigger_abbreviation(buffer) and self._should_trigger_window_title(windowName)
        else:
            return False
        
    def increment_usage_count(self):
        self.usageCount += 1
        if self.parent is not None:
            self.parent.increment_usage_count()
        
    def get_backspace_count(self, buffer):
        """
        Given the input buffer, calculate how many backspaces are needed to erase the text
        that triggered this folder.
        """
        if TriggerMode.ABBREVIATION in self.modes and self.backspace:
            if self._should_trigger_abbreviation(buffer):
                stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
                return len(self.abbreviation) + len(stringAfter)
        
        if self.parent is not None:
            return self.parent.get_backspace_count(buffer)

        return 0
    
    def calculate_input(self, buffer):
        """
        Calculate how many keystrokes were used in triggering this folder (if applicable).
        """
        if TriggerMode.ABBREVIATION in self.modes and self.backspace:
            if self._should_trigger_abbreviation(buffer):
                if self.immediate:
                    return len(self.abbreviation)
                else:
                    return len(self.abbreviation) + 1
                        
        if self.parent is not None:
            return self.parent.calculate_input(buffer)

        return 0        
        
    """def __cmp__(self, other):
        if self.usageCount != other.usageCount:
            return cmp(self.usageCount, other.usageCount)
        else:
            return cmp(other.title, self.title)"""
    
    def __str__(self):
        return self.title
    
    def __repr__(self):
        return str(self)


class TriggerMode:
    """
    Enumeration class for phrase match modes.
    
    NONE: Don't trigger this phrase (phrase will only be shown in its folder).
    ABBREVIATION: Trigger this phrase using an abbreviation.
    PREDICTIVE: Trigger this phrase using predictive mode.
    """
    NONE = 0
    ABBREVIATION = 1
    PREDICTIVE = 2
    HOTKEY = 3

class SendMode:
    """
    Enumeration class for phrase send modes

    KEYBOARD: Send using key events
    CB_CTRL_V: Send via clipboard and paste with Ctrl+v
    CB_CTRL_SHIFT_V: Send via clipboard and paste with Ctrl+Shift+v
    SELECTION: Send via X selection and paste with middle mouse button  
    """
    KEYBOARD = "kb"
    CB_CTRL_V = Key.CONTROL + "+v"
    CB_CTRL_SHIFT_V = Key.CONTROL + '+' + Key.SHIFT + "+v"
    CB_SHIFT_INSERT = Key.SHIFT + '+' + Key.INSERT
    SELECTION = None

SEND_MODES = {
             "Keyboard" : SendMode.KEYBOARD,
             "Clipboard (Ctrl+V)" : SendMode.CB_CTRL_V,
             "Clipboard (Ctrl+Shift+V)" : SendMode.CB_CTRL_SHIFT_V,
             "Clipboard (Shift+Insert)" : SendMode.CB_SHIFT_INSERT,
             "Mouse Selection" : SendMode.SELECTION
             }

class Phrase(AbstractAbbreviation, AbstractHotkey, AbstractWindowFilter):
    """
    Encapsulates all data and behaviour for a phrase.
    """
    
    def __init__(self, description, phrase):
        AbstractAbbreviation.__init__(self)
        AbstractHotkey.__init__(self)
        AbstractWindowFilter.__init__(self)
        self.description = description
        self.phrase = phrase
        self.modes = []
        self.usageCount = 0
        self.prompt = False
        self.omitTrigger = False
        self.matchCase = False
        self.parent = None
        self.showInTrayMenu = False
        self.sendMode = SendMode.KEYBOARD

    def get_serializable(self):
        d = {
            "type": "phrase",
            "description": self.description,
            "phrase": self.phrase,
            "modes": self.modes,
            "usageCount": self.usageCount,
            "prompt": self.prompt,
            "omitTrigger": self.omitTrigger,
            "matchCase": self.matchCase,
            "showInTrayMenu": self.showInTrayMenu,
            "abbreviation": AbstractAbbreviation.get_serializable(self),
            "hotkey": AbstractHotkey.get_serializable(self),
            "filter": AbstractWindowFilter.get_serializable(self),
            "sendMode" : self.sendMode
            }
        return d
        

    def load_from_serialized(self, data, parent):
        self.description = data["description"]
        self.phrase = data["phrase"]
        self.modes = data["modes"]
        self.usageCount = data["usageCount"]
        self.prompt = data["prompt"]
        self.omitTrigger = data["omitTrigger"]
        self.matchCase = data["matchCase"]
        self.parent = parent
        self.showInTrayMenu = data["showInTrayMenu"]
        self.sendMode = get_value_or_default(data, "sendMode", SendMode.KEYBOARD)
        AbstractAbbreviation.load_from_serialized(self, data["abbreviation"])
        AbstractHotkey.load_from_serialized(self, data["hotkey"])
        AbstractWindowFilter.load_from_serialized(self, data["filter"])
        
    def copy(self, thePhrase):
        self.description = thePhrase.description
        self.phrase = thePhrase.phrase
        
        # TODO - re-enable me if restoring predictive functionality
        #if TriggerMode.PREDICTIVE in thePhrase.modes:
        #    self.modes.append(TriggerMode.PREDICTIVE)
        
        self.prompt = thePhrase.prompt
        self.omitTrigger = thePhrase.omitTrigger
        self.matchCase = thePhrase.matchCase 
        self.parent = thePhrase.parent
        self.showInTrayMenu = thePhrase.showInTrayMenu
        self.copy_abbreviation(thePhrase)
        self.copy_hotkey(thePhrase)
        self.copy_window_filter(thePhrase)

    def get_tuple(self):
        return ("edit-paste", self.description, self.get_abbreviation(), self.get_hotkey_string(), self)
        
    def set_modes(self, modes):
        self.modes = modes

    def check_input(self, buffer, windowName):
        if self._should_trigger_window_title(windowName):
            abbr = False
            predict = False
            
            if TriggerMode.ABBREVIATION in self.modes:
                abbr = self._should_trigger_abbreviation(buffer)
            
            # TODO - re-enable me if restoring predictive functionality
            #if TriggerMode.PREDICTIVE in self.modes:
            #    predict = self._should_trigger_predictive(buffer)
            
            return (abbr or predict)
            
        return False
    
    def build_phrase(self, buffer):
        self.usageCount += 1
        self.parent.increment_usage_count()
        expansion = Expansion(self.phrase)
        triggerFound = False
        
        if TriggerMode.ABBREVIATION in self.modes:
            if self._should_trigger_abbreviation(buffer):
                stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
                triggerFound = True        
                if self.backspace:
                    # determine how many backspaces to send
                    expansion.backspaces = len(self.abbreviation) + len(stringAfter)
                else:
                    expansion.backspaces = len(stringAfter)
                
                if not self.omitTrigger:
                    expansion.string += stringAfter
                    
                if self.matchCase:
                    if typedAbbr.istitle():
                        expansion.string = expansion.string.capitalize()
                    elif typedAbbr.isupper():
                        expansion.string = expansion.string.upper()
                    elif typedAbbr.islower():
                        expansion.string = expansion.string.lower()
                        
        # TODO - re-enable me if restoring predictive functionality
        #if TriggerMode.PREDICTIVE in self.modes:
        #    if self._should_trigger_predictive(buffer):
        #        expansion.string = expansion.string[ConfigManager.SETTINGS[PREDICTIVE_LENGTH]:]
        #        triggerFound = True
            
        if not triggerFound:
            # Phrase could have been triggered from menu - check parents for backspace count
            expansion.backspaces = self.parent.get_backspace_count(buffer)
        
        #self.__parsePositionTokens(expansion)
        return expansion
    
    def calculate_input(self, buffer):
        """
        Calculate how many keystrokes were used in triggering this phrase.
        """
        if TriggerMode.ABBREVIATION in self.modes:
            if self._should_trigger_abbreviation(buffer):
                if self.immediate:
                    return len(self.abbreviation)
                else:
                    return len(self.abbreviation) + 1
        
        # TODO - re-enable me if restoring predictive functionality
        #if TriggerMode.PREDICTIVE in self.modes:
        #    if self._should_trigger_predictive(buffer):
        #        return ConfigManager.SETTINGS[PREDICTIVE_LENGTH]
            
        if TriggerMode.HOTKEY in self.modes:
            if buffer == '':
                return len(self.modifiers) + 1
            
        return self.parent.calculate_input(buffer)
        
        
    def get_trigger_chars(self, buffer):
        stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
        return typedAbbr + stringAfter
    
    def should_prompt(self, buffer):
        """
        Get a value indicating whether the user should be prompted to select the phrase.
        Always returns true if the phrase has been triggered using predictive mode.
        """
        # TODO - re-enable me if restoring predictive functionality
        #if TriggerMode.PREDICTIVE in self.modes:
        #    if self._should_trigger_predictive(buffer):
        #        return True
        
        return self.prompt
    
    def get_description(self, buffer):
        # TODO - re-enable me if restoring predictive functionality
        #if self._should_trigger_predictive(buffer):
        #    length = ConfigManager.SETTINGS[PREDICTIVE_LENGTH]
        #    endPoint = length + 30
        #    if len(self.phrase) > endPoint:
        #        description = "... " + self.phrase[length:endPoint] + "..."
        #    else:
        #        description = "... " + self.phrase[length:]
        #    description = description.replace('\n', ' ')
        #    return description
        #else:
        return self.description
    
    # TODO - re-enable me if restoring predictive functionality
    """def _should_trigger_predictive(self, buffer):
        if len(buffer) >= ConfigManager.SETTINGS[PREDICTIVE_LENGTH]: 
            typed = buffer[-ConfigManager.SETTINGS[PREDICTIVE_LENGTH]:]
            return self.phrase.startswith(typed)
        else:
            return False"""
        
    def parsePositionTokens(self, expansion):
        # Check the string for cursor positioning token and apply lefts and ups as appropriate
        if CURSOR_POSITION_TOKEN in expansion.string:
            firstpart, secondpart = expansion.string.split(CURSOR_POSITION_TOKEN)
            foundNavigationKey = False
            
            for key in NAVIGATION_KEYS:
                if key in expansion.string:
                    expansion.lefts = 0
                    foundNavigationKey = True
                    break
            
            if not foundNavigationKey:
                k = Key()
                for section in KEY_SPLIT_RE.split(secondpart):
                    if not k.is_key(section) or section in [' ', '\n']:
                        expansion.lefts += len(section)
            
            expansion.string = firstpart + secondpart
            
    def __str__(self):
        return self.description
    
    def __repr__(self):
        return "Phrase('" + self.description + "')"

class Expansion:
    
    def __init__(self, string):
        self.string = string
        self.lefts = 0
        self.backspaces = 0

class Script(AbstractAbbreviation, AbstractHotkey, AbstractWindowFilter):
    """
    Encapsulates all data and behaviour for a script.
    """
    
    def __init__(self, description, code):
        AbstractAbbreviation.__init__(self)
        AbstractHotkey.__init__(self)
        AbstractWindowFilter.__init__(self)
        self.description = description
        self.code = code
        self.store = Store()
        self.modes = []
        self.usageCount = 0
        self.prompt = False
        self.omitTrigger = False
        self.parent = None
        self.showInTrayMenu = False

    def get_serializable(self):
        d = {
            "type": "script",
            "description": self.description,
            "code": self.code,
            "store": self.store,
            "modes": self.modes,
            "usageCount": self.usageCount,
            "prompt": self.prompt,
            "omitTrigger": self.omitTrigger,
            "showInTrayMenu": self.showInTrayMenu,
            "abbreviation": AbstractAbbreviation.get_serializable(self),
            "hotkey": AbstractHotkey.get_serializable(self),
            "filter": AbstractWindowFilter.get_serializable(self)
            }
        return d


    def load_from_serialized(self, data, parent):
        self.description = data["description"]
        self.code = data["code"]
        self.store = Store(data["store"])
        self.modes = data["modes"]
        self.usageCount = data["usageCount"]
        self.prompt = data["prompt"]
        self.omitTrigger = data["omitTrigger"]
        self.parent = parent
        self.showInTrayMenu = data["showInTrayMenu"]
        AbstractAbbreviation.load_from_serialized(self, data["abbreviation"])
        AbstractHotkey.load_from_serialized(self, data["hotkey"])
        AbstractWindowFilter.load_from_serialized(self, data["filter"])

    def copy(self, theScript):
        self.description = theScript.description
        self.code = theScript.code
        
        self.prompt = theScript.prompt
        self.omitTrigger = theScript.omitTrigger
        self.parent = theScript.parent
        self.showInTrayMenu = theScript.showInTrayMenu
        self.copy_abbreviation(theScript)
        self.copy_hotkey(theScript)
        self.copy_window_filter(theScript)

    def get_tuple(self):
        return ("text-x-script", self.description, self.get_abbreviation(), self.get_hotkey_string(), self)

    def set_modes(self, modes):
        self.modes = modes

    def check_input(self, buffer, windowName):
        if self._should_trigger_window_title(windowName):            
            if TriggerMode.ABBREVIATION in self.modes:
                return self._should_trigger_abbreviation(buffer)
            
        return False
        
    def process_buffer(self, buffer):
        self.usageCount += 1
        self.parent.increment_usage_count()
        triggerFound = False
        backspaces = 0
        string = ""
        
        if TriggerMode.ABBREVIATION in self.modes:
            if self._should_trigger_abbreviation(buffer):
                stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
                triggerFound = True        
                if self.backspace:
                    # determine how many backspaces to send
                    backspaces = len(self.abbreviation) + len(stringAfter)
                else:
                    backspaces = len(stringAfter)
                    
                if not self.omitTrigger:
                    string += stringAfter

                
        if not triggerFound:
            # Phrase could have been triggered from menu - check parents for backspace count
            backspaces = self.parent.get_backspace_count(buffer)
            
        return backspaces, string
        

    def should_prompt(self, buffer):
        return self.prompt
    
    def get_description(self, buffer):
        return self.description

    def __str__(self):
        return self.description
    
    def __repr__(self):
        return "Script('" + self.description + "')"