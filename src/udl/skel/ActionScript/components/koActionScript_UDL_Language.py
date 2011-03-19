# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

# Komodo ActionScript language service.
#
# Generated by 'luddite.py' on Fri Mar 16 09:45:52 2007.
#

import logging
from koLanguageServiceBase import *
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koActionScriptLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language ActionScript")
    registry.registerLanguage(KoActionScriptLanguage())


class KoActionScriptLanguage(KoUDLLanguage):
    name = "ActionScript"
    lexresLangName = "ActionScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{4dd22f3a-52e2-426d-8a21-6f7ea2ba91ac}"
    defaultExtension = '.as'

    lang_from_udl_family = {'CSL': 'ActionScript', 'M': 'HTML'}

    # Code from koJavaScriptLanguage.py
    
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']
    searchURL = "http://www.google.com/search?q=site%3Aadobe.com%20ActionScript%20Reference+%W"
    namedBlockDescription = 'ActiveScript functions and classes'
    namedBlockRE = r'^[ |\t]*?(?:([\w|\.|_]*?)\s*=\s*function|function\s*([\w|\_]*?)|([\w|\_]*?)\s*:\s*function).*?$'
    supportsSmartIndent = "brace"
    
    sample = """function chkrange(elem,minval,maxval) {
    // Comment
    if (elem.value < minval - 1 ||
        elem.value > maxval + 1) {
          alert("Value of " + elem.name + " is out of range!");
    }
}
"""

from xpcom import components, nsError, ServerException
from koLintResult import *
from koLintResults import koLintResults
import os, re, sys, string
import os.path
import tempfile
import process
import koprocessutils

def ActionScriptWarnsToLintResults(warns, filename, code, status):
    defaultSeverity = ((status == 0 and KoLintResult.SEV_WARNING)
                       or KoLintResult.SEV_ERROR)
    lintResults = koLintResults()
    warnRe = re.compile(r'(?P<fileName>.*?):(?P<lineNum>\d+): (?:characters (?P<rangeStart>\d+)-(?P<rangeEnd>\d+))\s*:\s*(?P<message>.*)')
    for warn in warns:
        match = warnRe.search(warn)
        if match and match.group('fileName') == filename:
            lineNum = int(match.group('lineNum'))
            rangeStart = match.groupdict().get('rangeStart', None)
            rangeEnd = match.groupdict().get('rangeEnd', None)
            lr = KoLintResult()
            lr.description = match.group('message')
            lr.lineStart = lineNum 
            lr.lineEnd = lineNum
            if rangeStart and rangeEnd:
                lr.columnStart = int(rangeStart) + 1
                lr.columnEnd = int(rangeEnd) + 1
            else:
                lr.columnStart = 1
                lr.columnEnd = len(lines[lr.lineStart - 1]) + 1
            lr.severity = defaultSeverity
            lintResults.addResult(lr)
        else:
            log.debug("%s: no match", warn)
    log.debug("returning %d lint results", lintResults.getNumResults())
    return lintResults

class koActionScriptLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo ActionScript MTASC Linter"
    _reg_clsid_ = "{50bc6a5c-950f-4b94-8d5a-194524d41f85}"
    _reg_contractid_ = "@activestate.com/koLinter?language=ActionScript;1"
    _reg_categories_ = [ 
         ("category-komodo-linter", 'ActionScript'),
         ("komodo-linter", "ActionScript MTASC Linter"), ]

    def __init__(self):
        log.debug("Created the ActionScript Linter object")
        # Copied and pasted from KoPerlCompileLinter
        self.sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
            getService(components.interfaces.koISysUtils)
        self.infoSvc = components.classes["@activestate.com/koInfoService;1"].\
                       getService()
        self._lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
            getService(components.interfaces.koILastErrorService)
        self._koVer = self.infoSvc.version

    def _getInterpreter(self, prefset):
        if prefset.hasStringPref("actionScriptDefaultInterpreter") and\
           prefset.getStringPref("actionScriptDefaultInterpreter"):
            return prefset.getStringPref("actionScriptDefaultInterpreter")
        return None

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        prefset = request.koDoc.getEffectivePrefs()
        ascExe = self._getInterpreter(prefset)
        if ascExe is None:
            lintResults = koLintResults()
            lr = KoLintResult()
            lr.description = "Can't find an ActionScript interpreter"
            lr.lineStart = lr.lineEnd = 1
            lr.columnStart = 1
            lr.columnEnd = 1 + len(text.splitlines()[0])
            lr.severity = KoLintResult.SEV_WARNING
            lintResults.addResult(lr)
            log.debug('no interpreter')
            return lintResults
        tmpFileName = None
        cwd = request.cwd
        if cwd:
            tmpFileName = os.path.join(cwd,
                                       "tmp_ko_aslint_ko%s.as" % (self._koVer.replace(".","_").replace("-","_")))
            try:
                fout = open(tmpFileName, 'wb')
                fout.write(text)
                fout.close()
            except (OSError, IOError), ex:
                tmpFileName = None
        if not tmpFileName:
            # Fallback to using a tmp dir if cannot write in cwd.
            try:
                tmpFileName = tempfile.mktemp()
                cwd = os.path.dirname(tmpFileName)
            except OSError, ex:
                # Sometimes get this error but don't know why:
                # OSError: [Errno 13] Permission denied: 'C:\\DOCUME~1\\trentm\\LOCALS~1\\Temp\\~1324-test'
                errmsg = "error determining temporary filename for "\
                         "ActionScript content: %s" % ex
                self._lastErrorSvc.setLastError(3, errmsg)
                raise ServerException(nsError.NS_ERROR_UNEXPECTED)
            fout = open(tmpFileName, 'wb')
            fout.write(text)
            fout.close()

        try:
            argv = [ascExe, "-strict"]
            # mtasc gets confused by pathnames
            mtasc_filename = os.path.basename(tmpFileName)
            argv += [mtasc_filename]
            cwd = cwd or None # convert '' to None (cwd=='' for new files)
            log.debug("Run cmd %s in dir %s", " ".join(argv), cwd)
            env = koprocessutils.getUserEnv()
            p = process.ProcessOpen(argv, cwd=cwd, env=env)
            results = p.stderr.readlines()
            log.debug("results: %s", "\n".join(results))
            p.close()
            status = None
            try:
                raw_status = p.wait(timeout=3.0)
                if sys.platform.startswith("win"):
                    status = raw_status
                else:
                    status = raw_status >> 8
            
                lintResults = ActionScriptWarnsToLintResults(results, mtasc_filename, text, status)
            except process.ProcessError:
                # Don't do anything with this exception right now.
                lintResults = None
                log.debug("Waiting for as linter, got a ProcessError")
            
        finally:
            os.unlink(tmpFileName)

        return lintResults

# extra comment to force rebuild
