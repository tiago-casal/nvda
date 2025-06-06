# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2023-2024 NV Access Limited, Leonard de Ruijter

"""Unit tests for braille cursor routing."""

import config
import braille
import textInfos
import api
import controlTypes
from ..textProvider import CursorManager, BasicTextProvider
import unittest
import time
from config.featureFlagEnums import ReviewRoutingMovesSystemCaretFlag


class CursorManagerTextInfo(CursorManager.TextInfo):
	def updateCaret(self):
		super().updateCaret()
		self.obj.caretLastUpdateTime = time.time()

	def activate(self):
		self.obj.lastActivateTime = time.time()


class CursorManager(CursorManager):
	caretLastUpdateTime: float = 0.0
	lastActivateTime: float = 0.0
	TextInfo = CursorManagerTextInfo


class TestReviewRoutingMovesSystemCaretInNavigableText(unittest.TestCase):
	"""A test for the move system caret when routing review cursor braille setting
	when operating in navigable text with object review.
	"""

	cm: CursorManager

	def setUp(self):
		# Set tethering to review.
		braille.handler.setTether(braille.TetherTo.REVIEW.value)
		cmText = "the quick brown fox jumps over the lazy dog"
		cm = self.cm = CursorManager(text=cmText)
		cm.role = controlTypes.Role.EDITABLETEXT
		caret = self.caret = cm.makeTextInfo(textInfos.POSITION_CARET)
		api.setReviewPosition(caret)
		braille.handler.handleReviewMove()

	def test_moveCaret_never_moveReviewAndActivate(self):
		"""Test that routing action on a cell will move the review cursor when routing changes the position,
		whereas it should activate the current position when the review cursor is already at that position.
		The caret should never move.
		"""
		config.conf["braille"]["reviewRoutingMovesSystemCaret"] = ReviewRoutingMovesSystemCaretFlag.NEVER.name
		curTime = time.time()
		braille.handler.routeTo(3)  # Route to the fourth cell
		self.assertLess(self.cm.lastActivateTime, curTime)
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		self.assertEqual(caret, self.caret)
		expectedReview = self.caret.copy()
		expectedReview.move(textInfos.UNIT_CHARACTER, 3)
		self.assertEqual(expectedReview, api.getReviewPosition())
		braille.handler.routeTo(4)  # Route to the fifth cell
		# Object still not activated as no second routing press on same cell.
		self.assertLess(self.cm.lastActivateTime, curTime)
		# The caret shouldn't have been moved either
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		self.assertEqual(caret, self.caret)
		# move expected review from cell 4 to 5
		expectedReview.move(textInfos.UNIT_CHARACTER, 1)
		self.assertEqual(expectedReview, api.getReviewPosition())
		# Route a second time to activate the object under the cell
		braille.handler.routeTo(4)
		self.assertGreaterEqual(self.cm.lastActivateTime, curTime)
		# While the object is now activated, caret should have been steady.
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		self.assertEqual(caret, self.caret)

	def test_moveCaret_never_instantActivate(self):
		"""Test that routing action on a cell will activate the current position
		when the review cursor is already at that position.
		This test ensures that this behavior will work, even when it is the first routing action in a sequence.
		The caret should never move.
		"""
		config.conf["braille"]["reviewRoutingMovesSystemCaret"] = ReviewRoutingMovesSystemCaretFlag.NEVER.name
		curTime = time.time()
		review = self.caret.copy()
		review.move(textInfos.UNIT_CHARACTER, 3)
		api.setReviewPosition(review)
		# Route to the fourth cell to activate the object under the cell,
		# since the review cursor is already on that cell.
		braille.handler.routeTo(3)
		self.assertGreaterEqual(self.cm.lastActivateTime, curTime)
		# While the object is now activated, caret should have been steady.
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		self.assertEqual(caret, self.caret)

	def test_moveCaret_always_moveReviewAndActivate(self):
		"""Test that routing action on a cell will move the review cursor when routing changes the position,
		whereas it should activate the current position when the review cursor is already at that position.
		The caret should always move when routing.
		"""
		config.conf["braille"]["reviewRoutingMovesSystemCaret"] = (
			ReviewRoutingMovesSystemCaretFlag.ALWAYS.name
		)
		curTime = time.time()
		braille.handler.routeTo(3)  # Route to the fourth cell
		self.assertLess(self.cm.lastActivateTime, curTime)
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		expectedReview = self.caret.copy()
		expectedReview.move(textInfos.UNIT_CHARACTER, 3)
		self.assertEqual(expectedReview, api.getReviewPosition())
		self.assertEqual(caret, expectedReview)
		braille.handler.routeTo(4)  # Route to the fifth cell
		# Object still not activated as no second routing press on same cell.
		self.assertLess(self.cm.lastActivateTime, curTime)
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		# move expected review from cell 4 to 5
		expectedReview.move(textInfos.UNIT_CHARACTER, 1)
		self.assertEqual(expectedReview, api.getReviewPosition())
		self.assertEqual(caret, expectedReview)
		# Route a second time to activate the object under the cell
		braille.handler.routeTo(4)
		self.assertGreaterEqual(self.cm.lastActivateTime, curTime)
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		self.assertEqual(caret, expectedReview)

	def test_moveCaret_always_instantActivate(self):
		"""Test that routing action on a cell will activate the current position
		when the review cursor is already at that position.
		This test ensures that this behavior will work, even when it is the first routing action in a sequence.
		The caret should also have been moved even though routing didn't touch the review cursor position.
		"""
		config.conf["braille"]["reviewRoutingMovesSystemCaret"] = (
			ReviewRoutingMovesSystemCaretFlag.ALWAYS.name
		)
		curTime = time.time()
		review = self.caret.copy()
		review.move(textInfos.UNIT_CHARACTER, 3)
		api.setReviewPosition(review)
		self.assertNotEqual(self.caret, review)
		# Route to the fourth cell to activate the object under the cell,
		# since the review cursor is already on that cell.
		braille.handler.routeTo(3)
		self.assertGreaterEqual(self.cm.lastActivateTime, curTime)
		caret = self.cm.makeTextInfo(textInfos.POSITION_CARET)
		self.assertEqual(caret, review)


class TestTextInfoRegionRouting(unittest.TestCase):
	"""A test for TextInfoRegion.getTextInfoForBraillePos, which is used in braille cursor routing.
	This test ensures that braille routes to the expected character when dealing with emoji
	or other composites.
	These glyphs are threated as one character by uniscribe, however they span multiple characters
	on a braille display.
	Note that due to the nature of this test, it relies on uniscribe to be available.
	"""

	def test_routeToEmoji(self):
		testText = "⚠️test"
		obj = BasicTextProvider(text=testText)
		ti = obj.makeTextInfo(textInfos.POSITION_CARET)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[:2])
		ti.collapse(end=True)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[2])
		region = braille.TextInfoRegion(obj)
		region.update()
		index = 3  # Position of e
		pos = region.rawToBraillePos[index]
		region.routeTo(pos)
		ti = obj.makeTextInfo(textInfos.POSITION_CARET)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[index])

	def test_routeToComposite(self):
		testText = "רבְּר"
		obj = BasicTextProvider(text=testText)
		ti = obj.makeTextInfo(textInfos.POSITION_CARET)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[0])
		ti.collapse(end=True)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[1:4])
		ti.collapse(end=True)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[4])
		region = braille.TextInfoRegion(obj)
		region.update()
		index = 1  # Position of ב
		pos = region.rawToBraillePos[index]
		region.routeTo(pos)
		ti = obj.makeTextInfo(textInfos.POSITION_CARET)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[1:4])
		index = 3  # Position of ּ (\u5bc)
		pos = region.rawToBraillePos[index]
		region.routeTo(pos)
		ti = obj.makeTextInfo(textInfos.POSITION_CARET)
		ti.expand(textInfos.UNIT_CHARACTER)
		self.assertEqual(ti.text, testText[1:4])
