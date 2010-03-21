from unittest import TestCase

from zope.component import provideAdapter
from zope.interface import implements
from zope.interface import Interface
from zope.testing import cleanup

from Acquisition import Explicit
from Products.CMFCore.utils import getToolByName

from Products.LinguaPlone.browser.selector import TranslatableLanguageSelector
from Products.LinguaPlone.interfaces import ITranslatable
from Products.LinguaPlone.tests import LinguaPloneTestCase
from Products.LinguaPlone.tests.utils import makeContent
from Products.LinguaPlone.tests.utils import makeTranslation


class Dummy(Explicit):

    implements(ITranslatable)

    def objectIds(self):
        return ()

    def getPortalObject(self):
        return self

    def absolute_url(self):
        return 'absolute url'

    def getTranslations(self, review_state=False):
        return {'en': self, 'nl': self}

    def getPhysicalPath(self):
        return getattr(self, 'physicalpath', [])


class DummyRequest(object):

    form = {}

    def get(self, key, default):
        return self.__dict__.get(key, default)


class DummyState(object):

    def __init__(self, context, request):
        pass

    def canonical_object_url(self):
        return 'object_url'


class MockLanguageTool(object):

    use_cookie_negotiation = True

    def showFlags(self):
        return True

    def getAvailableLanguageInformation(self):
        return dict(en={'selected': True}, de={'selected': False},
                    nl={'selected': True})

    def getLanguageBindings(self):
        # en = selected by user, nl = default, [] = other options
        return ('en', 'nl', [])

    def getSupportedLanguages(self):
        return ['nl', 'en']


class TestLanguageSelectorBasics(cleanup.CleanUp, TestCase):

    def setUp(self):
        provideAdapter(DummyState, adapts=(Dummy, DummyRequest),
                       provides=Interface, name="plone_context_state")
        self.context = Dummy()
        self.context.portal_url = Dummy()
        self.container = Dummy()
        self.context = self.context.__of__(self.container)
        self.request = DummyRequest()
        self.selector = TranslatableLanguageSelector(self.context,
                            self.request, None, None)


    def testLanguages(self):
        self.selector.update()
        self.selector.tool = MockLanguageTool()
        self.assertEqual(self.selector.languages(),
                [{'code': 'nl',
                  'translated': True,
                  'selected': False,
                  'url': 'object_url?set_language=nl',
                 },
                 {'code': 'en',
                  'translated': True,
                  'selected': True,
                  'url': 'object_url?set_language=en',
                 },
                 ])

    def testPreserveViewAndQuery(self):
        self.context.physicalpath = ['', 'fake', 'path']
        self.request.PATH_INFO = '/fake/path/to/object'
        self.request.form['variable'] = u'pres\xd8rved'
        self.selector.update()
        self.selector.tool = MockLanguageTool()
        base = 'object_url/to/object?variable='
        expected = [{'code': 'nl',
                     'translated': True,
                     'selected': False,
                     'url': base + 'pres%C3%98rved&set_language=nl',
                    },
                    {'code': 'en',
                     'translated': True,
                     'selected': True,
                     'url': base + 'pres%C3%98rved&set_language=en',
                    }]
        self.assertEqual(self.selector.languages(), expected)


class TestLanguageSelectorRendering(LinguaPloneTestCase.LinguaPloneTestCase):

    def afterSetUp(self):
        self.addLanguage('de')
        self.addLanguage('no')
        self.setLanguage('en')
        self.english = makeContent(self.folder, 'SimpleType', 'doc')
        self.english.setLanguage('en')
        self.german = makeTranslation(self.english, 'de')
        self.german.setLanguage('de')

    def testRenderSelector(self):
        request = self.app.REQUEST
        selector = TranslatableLanguageSelector(
            self.english, request, None, None)
        selector.update()
        output = selector.render()
        self.assert_('<ul id="portal-languageselector"' in output)
        en_path = self.english.absolute_url()
        en_link = '<a href="%s?set_language=en"' % en_path
        self.assert_(en_link in output)
        de_path = self.german.absolute_url()
        de_link = '<a href="%s?set_language=de"' % de_path
        self.assert_(de_link in output)
        no_path = self.portal.absolute_url()
        no_link = '<a href="%s?set_language=no"' % no_path
        self.assert_(no_link in output)

    def testRenderSelectorOnSiteRoot(self):
        request = self.app.REQUEST
        selector = TranslatableLanguageSelector(
            self.portal, request, None, None)
        selector.update()
        output = selector.render()
        path = self.portal.absolute_url()
        de_link = '<a href="%s?set_language=de"' % path
        self.assert_(de_link in output)
        en_link = '<a href="%s?set_language=en"' % path
        self.assert_(en_link in output)

    def testRenderSelectorWithFlags(self):
        request = self.app.REQUEST
        ltool = getToolByName(self.portal, 'portal_languages')
        ltool.display_flags = True
        selector = TranslatableLanguageSelector(
            self.english, request, None, None)
        selector.update()
        output = selector.render()
        self.assert_('de.gif' in output)
        self.assert_('gb.gif' in output)

    def testRenderSelectorWithoutCookieNegotiation(self):
        request = self.app.REQUEST
        ltool = getToolByName(self.portal, 'portal_languages')
        ltool.use_cookie_negotiation = False
        selector = TranslatableLanguageSelector(
            self.english, request, None, None)
        selector.update()
        output = selector.render()
        self.assertEquals(output.strip(), u'')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestLanguageSelectorBasics))
    suite.addTest(makeSuite(TestLanguageSelectorRendering))
    return suite