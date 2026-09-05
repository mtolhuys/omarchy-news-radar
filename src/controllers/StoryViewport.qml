import QtQuick

// Owns selection and the visual anchor across model replacement and pagination.
Item {
  id: root
  property var stories: []
  property int selectedIndex: 0
  property int storyViewportAnchorIndex: 0
  property int storyViewportRevision: 0
  property bool pendingViewportPreservation: false
  property real pendingViewportContentY: 0
  property int pendingViewportAnchorIndex: -1
  property real pendingViewportAnchorTop: 0
  property int pendingViewportRevision: -1
  property int pendingViewportAttempts: 0
  property int forcedTopAnchorIndex: -1
  readonly property var selectedStory: selectedIndex >= 0 && selectedIndex < stories.length ? stories[selectedIndex] : null
  property alias model: renderedStoryModel
  property alias animation: storyScrollAnimation
  property alias preservationTimer: viewportPreservationTimer
  required property var storyList
  required property var loadMoreButton
  property bool hasMoreStories: false
  signal selected(bool markRead)
  signal navigationRequested()
  signal projectionApplied()
  NumberAnimation {
    id: storyScrollAnimation
    target: storyList
    property: "contentY"
    duration: 140
    easing.type: Easing.OutCubic
    onStopped: root.applyPendingViewportPreservation()
  }

  Timer {
    id: viewportPreservationTimer
    interval: 16
    repeat: true
    onTriggered: root.applyPendingViewportPreservation()
  }

  ListModel {
    id: renderedStoryModel
    dynamicRoles: true
  }

  function restoreStoryViewport(revision) {
    if (revision !== undefined && revision !== storyViewportRevision) return
    if (!stories.length || selectedIndex < 0) return
    storyScrollAnimation.stop()
    if (hasMoreStories && selectedIndex === stories.length - 1)
      storyList.positionViewAtEnd()
    else {
      var anchorIndex = Math.max(
        0,
        Math.min(selectedIndex, storyViewportAnchorIndex)
      )
      storyViewportAnchorIndex = anchorIndex
      storyList.positionViewAtIndex(anchorIndex, ListView.Beginning)
    }
  }

  function queueViewportPreservation(contentY, anchorIndex, anchorTop, revision) {
    pendingViewportPreservation = true
    pendingViewportContentY = contentY
    pendingViewportAnchorIndex = anchorIndex
    pendingViewportAnchorTop = forcedTopAnchorIndex === anchorIndex ? 0 : anchorTop
    pendingViewportRevision = revision
    pendingViewportAttempts = 24
    viewportPreservationTimer.start()
    // Correct the model-replacement offset in this turn so the retained row
    // never flashes at its provisional delegate position. The timer then
    // keeps the same anchor stable across subsequent rendered frames.
    applyPendingViewportPreservation()
  }

  function applyPendingViewportPreservation() {
    if (!pendingViewportPreservation) return
    if (pendingViewportRevision !== storyViewportRevision) {
      pendingViewportPreservation = false
      pendingViewportAttempts = 0
      viewportPreservationTimer.stop()
      return
    }
    if (storyScrollAnimation.running) return
    var targetContentY = pendingViewportContentY
    var anchorRow = pendingViewportAnchorIndex >= 0
      ? storyList.itemAtIndex(pendingViewportAnchorIndex) : null
    if (pendingViewportAnchorIndex >= 0 && !anchorRow && pendingViewportAttempts > 0) {
      pendingViewportAttempts--
      storyList.positionViewAtIndex(pendingViewportAnchorIndex, ListView.Beginning)
      return
    }
    if (anchorRow) targetContentY = anchorRow.y - pendingViewportAnchorTop
    var maximumContentY = storyList.originY
      + Math.max(0, storyList.contentHeight - storyList.height)
    storyList.contentY = Math.max(
      storyList.originY,
      Math.min(targetContentY, maximumContentY)
    )
    if (anchorRow && pendingViewportAttempts > 0) {
      pendingViewportAttempts--
      return
    }
    pendingViewportPreservation = false
    pendingViewportAttempts = 0
    viewportPreservationTimer.stop()
  }

  function storyIndexById(eventId) {
    if (!eventId) return -1
    for (var index = 0; index < stories.length; index++) {
      if (stories[index] && String(stories[index].id) === eventId) return index
    }
    return -1
  }

  function syncRenderedStories(previousStories, nextStories, preserveViewport) {
    var sharedCount = Math.min(previousStories.length, nextStories.length)
    var stablePrefix = preserveViewport
    for (var index = 0; stablePrefix && index < sharedCount; index++) {
      var previousId = previousStories[index] && previousStories[index].id
        ? String(previousStories[index].id) : ""
      var nextId = nextStories[index] && nextStories[index].id
        ? String(nextStories[index].id) : ""
      if (!previousId || previousId !== nextId) stablePrefix = false
    }
    if (!stablePrefix) {
      renderedStoryModel.clear()
      for (var replacementIndex = 0; replacementIndex < nextStories.length; replacementIndex++)
        renderedStoryModel.append({ payload: nextStories[replacementIndex] })
      return
    }
    for (var retainedIndex = 0; retainedIndex < sharedCount; retainedIndex++) {
      // A read-state projection normally changes one payload. Reassigning
      // every unchanged map makes ListView relayout rows above the selection
      // and shifts the visual anchor even though their content is identical.
      if (JSON.stringify(previousStories[retainedIndex])
          !== JSON.stringify(nextStories[retainedIndex]))
        renderedStoryModel.setProperty(retainedIndex, "payload", nextStories[retainedIndex])
    }
    if (renderedStoryModel.count > nextStories.length)
      renderedStoryModel.remove(
        nextStories.length,
        renderedStoryModel.count - nextStories.length
      )
    for (var appendedIndex = renderedStoryModel.count; appendedIndex < nextStories.length; appendedIndex++)
      renderedStoryModel.append({ payload: nextStories[appendedIndex] })
  }

  function moveSelection(delta) {
    if (!stories.length) return
    if (loadMoreButton.activeFocus) {
      if (delta < 0) {
        // The final story remains selected while Load more owns focus. Returning
        // focus must not reposition or re-read that unchanged selection.
        navigationRequested()
      }
      return
    }
    if (delta > 0 && selectedIndex === stories.length - 1 && hasMoreStories) {
      loadMoreButton.forceActiveFocus(Qt.TabFocusReason)
      storyList.positionViewAtEnd()
      return
    }
    storyViewportRevision++
    storyScrollAnimation.stop()
    var viewportRevision = storyViewportRevision
    var nextIndex = Math.max(0, Math.min(stories.length - 1, selectedIndex + delta))
    forcedTopAnchorIndex = -1
    if (delta < 0) {
      var previousRow = storyList.itemAtIndex(nextIndex)
      var previousAboveViewport = !previousRow
        || previousRow.y - storyList.contentY < -0.5
      if (previousAboveViewport) {
        // Key repeat can outrun an eased scroll and leave the highlight above
        // the clip. Move the viewport first so selection is never invisible.
        storyList.positionViewAtIndex(nextIndex, ListView.Beginning)
        storyViewportAnchorIndex = nextIndex
      }
      selectStory(nextIndex, true)
      if (previousAboveViewport) {
        Qt.callLater(function() {
          if (root.selectedIndex === nextIndex
              && root.storyViewportRevision === viewportRevision)
            storyList.positionViewAtIndex(nextIndex, ListView.Beginning)
        })
      }
      return
    }
    var nextRowBeforeSelection = storyList.itemAtIndex(nextIndex)
    if (delta > 0 && !nextRowBeforeSelection) {
      // The first row revealed by pagination can still be virtualized just
      // outside the clip. Do not ask an animation to target geometry that Qt
      // has not created: select the canonical index and place it directly at
      // the top. Its read-state projection then preserves this real anchor.
      selectStory(nextIndex, true)
      storyViewportAnchorIndex = nextIndex
      forcedTopAnchorIndex = nextIndex
      storyList.positionViewAtIndex(nextIndex, ListView.Beginning)
      queueViewportPreservation(
        storyList.contentY,
        nextIndex,
        0,
        viewportRevision
      )
      return
    }
    var initialContentY = storyList.contentY
    var currentRow = delta > 0 ? storyList.itemAtIndex(selectedIndex) : null
    var fallbackNextTop = currentRow
      ? currentRow.y + currentRow.height + storyList.spacing : -1
    selectStory(nextIndex, true)
    Qt.callLater(function() {
      if (root.selectedIndex !== nextIndex
          || root.storyViewportRevision !== viewportRevision) return
      var anchorAtTop = storyNeedsTopAnchor(nextIndex)
      if (anchorAtTop) root.storyViewportAnchorIndex = nextIndex
      animateStoryPosition(nextIndex, anchorAtTop, initialContentY, fallbackNextTop)
    })
  }

  function storyNeedsTopAnchor(index) {
    var row = storyList.itemAtIndex(index)
    if (!row) {
      storyList.positionViewAtIndex(index, ListView.Contain)
      row = storyList.itemAtIndex(index)
    }
    if (!row) return true
    var top = row.y - storyList.contentY
    return top < -0.5 || top + row.height >= storyList.height - 0.5
  }

  function animateStoryPosition(index, alignAtTop, initialContentY, fallbackTargetY) {
    storyScrollAnimation.stop()
    var targetContentY = initialContentY
    if (alignAtTop) {
      storyList.positionViewAtIndex(index, ListView.Beginning)
      targetContentY = storyList.contentY
      var row = storyList.itemAtIndex(index)
      if (row) {
        var maximumContentY = storyList.originY
          + Math.max(0, storyList.contentHeight - storyList.height)
        targetContentY = Math.max(
          storyList.originY,
          Math.min(row.y, maximumContentY)
        )
      } else if (fallbackTargetY !== undefined && fallbackTargetY >= 0) {
        var fallbackMaximumY = storyList.originY
          + Math.max(0, storyList.contentHeight - storyList.height)
        targetContentY = Math.max(
          storyList.originY,
          Math.min(fallbackTargetY, fallbackMaximumY)
        )
      }
    }
    storyList.contentY = initialContentY
    if (Math.abs(targetContentY - initialContentY) <= 0.5) {
      storyList.contentY = targetContentY
      return
    }
    storyScrollAnimation.from = initialContentY
    storyScrollAnimation.to = targetContentY
    storyScrollAnimation.start()
  }

  function selectStory(index, markRead) {
    if (index < 0 || index >= stories.length) return
    selectedIndex = index
    selected(markRead)
  }

  function storyViewportState() {
    var row = selectedIndex >= 0 ? storyList.itemAtIndex(selectedIndex) : null
    var anchorRow = storyViewportAnchorIndex >= 0
      ? storyList.itemAtIndex(storyViewportAnchorIndex) : null
    if (!row) {
      return JSON.stringify({
        selectedIndex: selectedIndex,
        available: false,
        fullyVisible: false,
        topAligned: false,
        viewportHeight: storyList.height,
        contentY: storyList.contentY,
        contentHeight: storyList.contentHeight,
        listCount: storyList.count,
        anchorIndex: storyViewportAnchorIndex,
        scrolling: storyScrollAnimation.running
      })
    }
    var top = row.y - storyList.contentY
    var bottom = top + row.height
    var headline = row.headlineBounds()
    var anchorTop = anchorRow ? anchorRow.y - storyList.contentY : 0
    var anchorBottom = anchorRow ? anchorTop + anchorRow.height : 0
    return JSON.stringify({
      selectedIndex: selectedIndex,
      available: true,
      fullyVisible: top >= -0.5 && bottom <= storyList.height + 0.5,
      headlineFullyVisible: top + headline.top >= -0.5
        && top + headline.top + headline.height <= storyList.height + 0.5,
      topAligned: Math.abs(top) <= 1,
      top: top,
      bottom: bottom,
      viewportHeight: storyList.height,
      contentY: storyList.contentY,
      contentHeight: storyList.contentHeight,
      originY: storyList.originY,
      rowY: row.y,
      anchorIndex: storyViewportAnchorIndex,
      anchorAvailable: !!anchorRow,
      anchorTop: anchorTop,
      anchorFullyVisible: !!anchorRow
        && anchorTop >= -0.5 && anchorBottom <= storyList.height + 0.5,
      anchorTopAligned: !!anchorRow && Math.abs(anchorTop) <= 1,
      scrolling: storyScrollAnimation.running
    })
  }

  function applyProjection(result, viewportMode) {
      var preserveViewport = viewportMode === "preserve"
      var resumeTopAlignment = preserveViewport && storyScrollAnimation.running
      if (resumeTopAlignment) storyScrollAnimation.stop()
      var preservedContentY = storyList.contentY
      var preservedSelectedId = selectedStory && selectedStory.id
        ? String(selectedStory.id) : ""
      var preservedAnchorId = storyViewportAnchorIndex >= 0
          && storyViewportAnchorIndex < stories.length
          && stories[storyViewportAnchorIndex]
        ? String(stories[storyViewportAnchorIndex].id) : ""
      var preservedAnchorRow = storyViewportAnchorIndex >= 0
        ? storyList.itemAtIndex(storyViewportAnchorIndex) : null
      var preservedAnchorTop = preservedAnchorRow
        ? preservedAnchorRow.y - storyList.contentY : 0
      var preservedAnchor = storyViewportAnchorIndex
      var previousStories = stories
      stories = result.events || []
      syncRenderedStories(previousStories, stories, preserveViewport)
      var preservedSelectedIndex = preserveViewport
        ? storyIndexById(preservedSelectedId) : -1
      var preservedAnchorIndex = preserveViewport
        ? storyIndexById(preservedAnchorId) : -1
      selectedIndex = stories.length
        ? (preservedSelectedIndex >= 0
          ? preservedSelectedIndex
          : Math.min(Math.max(0, selectedIndex), stories.length - 1))
        : -1
      storyViewportAnchorIndex = stories.length
        ? Math.min(
          Math.max(0, preservedAnchorIndex >= 0 ? preservedAnchorIndex : preservedAnchor),
          selectedIndex
        )
        : -1
      if (forcedTopAnchorIndex === storyViewportAnchorIndex)
        preservedAnchorTop = 0
      if (preserveViewport) {
        // Replacing a ListView model may reset contentY while delegates settle.
        // Keep the reader at the exact live visual anchor. If a read-state
        // projection completed during a keyboard scroll, stop the obsolete
        // animation target, restore the current on-screen position against
        // the replacement delegates, then continue toward the new row's top.
        storyList.contentY = preservedContentY
        var preservedRevision = storyViewportRevision
        if (resumeTopAlignment) {
          var resumeAnchorIndex = storyViewportAnchorIndex
          Qt.callLater(function() {
            if (preservedRevision !== root.storyViewportRevision) return
            var resumeRow = storyList.itemAtIndex(resumeAnchorIndex)
            if (resumeRow) {
              var resumeMaximumY = storyList.originY
                + Math.max(0, storyList.contentHeight - storyList.height)
              storyList.contentY = Math.max(
                storyList.originY,
                Math.min(resumeRow.y - preservedAnchorTop, resumeMaximumY)
              )
            }
            root.animateStoryPosition(
              resumeAnchorIndex,
              true,
              storyList.contentY
            )
          })
        } else {
          queueViewportPreservation(
            preservedContentY,
            storyViewportAnchorIndex,
            preservedAnchorTop,
            preservedRevision
          )
        }
      } else {
        storyViewportRevision++
        var restoreRevision = storyViewportRevision
        Qt.callLater(function() { root.restoreStoryViewport(restoreRevision) })
      }
    projectionApplied()
  }
  function scrollPage(direction) {
    reset()
    storyViewportRevision++
    var minimum = storyList.originY
    var maximum = minimum + Math.max(0, storyList.contentHeight - storyList.height)
    storyList.contentY = Math.max(minimum, Math.min(storyList.contentY + direction * storyList.height * 0.8, maximum))
  }

  function reset() {
    storyScrollAnimation.stop()
    viewportPreservationTimer.stop()
    pendingViewportPreservation = false
    pendingViewportAttempts = 0
    forcedTopAnchorIndex = -1
  }
  function clear() {
    stories = []
    renderedStoryModel.clear()
    selectedIndex = -1
    storyViewportAnchorIndex = -1
  }
}
