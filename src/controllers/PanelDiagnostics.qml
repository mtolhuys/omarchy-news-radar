import QtQuick

// Read-only acceptance observability; no interaction or persistence belongs here.
Item {
  id: root
  required property var panel
  required property var session
  required property var actions
  required property var storyViewport
  required property var maintenance
  required property var windowLifecycle
  required property var sectionsModel
  required property var views
  function debugState() {
    var group = views.keySurface.narrow ? views.readerList.list.headerItem : views.inspectorView.group
    var controls = (panel.overviewVisible ? views.discoveryView.controlTargets() : views.briefingNotice.controlTargets().concat(group && group.visible ? group.controlTargets() : [])).concat(panel.overviewTools())
    var focusedControl = controls.filter(function(item) { return item.activeFocus })
    return JSON.stringify({
      build: panel.runtimeBuildIdentity,
      opened: panel.opened,
      section: sectionsModel.currentSection,
      selectedIndex: storyViewport.selectedIndex,
      selectedId: storyViewport.selectedStory ? storyViewport.selectedStory.id : "",
      selectedTitle: storyViewport.selectedStory ? storyViewport.selectedStory.title : "",
      selectedHasImage: storyViewport.selectedStory ? !!storyViewport.selectedStory.imageUrl : false,
      selectedMetricIds: storyViewport.selectedStory && storyViewport.selectedStory.metricItems
        ? storyViewport.selectedStory.metricItems.map(function(metric) { return metric.id }) : [],
      selectedMarketplaceUrl: storyViewport.selectedStory ? String(storyViewport.selectedStory.marketplaceUrl || "") : "",
      inspectorVisible: views.inspectorView.visible,
      readerActionsEnabled: !!storyViewport.selectedStory,
      emptyRecoveryLabel: panel.emptyRecoveryLabel(),
      selectedIsUnread: storyViewport.selectedStory ? storyViewport.selectedStory.isUnread === true : false,
      storyCount: storyViewport.stories.length,
      status: session.feedStatus,
      editionMode: session.editionMode,
      publisherStale: session.editionTiming.publisherStale === true,
      timing: session.editionTiming,
      statusDetail: session.statusDetail,
      noCacheNoticeVisible: views.masthead.noCacheNotice.visible,
      availableImageCount: session.availableImageCount,
      refreshing: session.refreshing,
      refreshIndicatorVisible: views.masthead.refreshButton.iconSpinning,
      refreshTooltipVisible: views.masthead.refreshButton.tooltipVisible,
      helperRunning: panel.anyHelperRunning,
      localStateReady: session.localStateReady,
      barVisiblePreference: session.preferences.barVisible !== false,
      searchFocused: views.masthead.search.activeFocus,
      unreadCount: Number(session.unreadCounts[sectionsModel.currentSection] || 0),
      bulkReadInFlight: actions.bulkReadInFlight,
      preferencesOpen: panel.preferencesOpen,
      sectionSettingsOpen: panel.sectionSettingsOpen,
      totalStories: session.totalStories,
      hasMoreStories: session.hasMoreStories,
      loadMoreFocused: views.readerList.loadMoreButton.activeFocus,
      loadMoreLabel: views.readerList.loadMoreButton.label,
      sectionLimit: Number(sectionsModel.sectionLimits[sectionsModel.currentSection] || sectionsModel.pageSize),
      pendingProjection: session.pendingProjection,
      projecting: session.projecting,
      filterSummary: session.filterSummary,
      retainedReadStories: session.retainedReadStories,
      sectionName: sectionsModel.currentProfile.name,
      sectionRail: JSON.parse(sectionRailGeometry()),
      sectionSources: session.sectionSources,
      windowVisible: views.panelWindow.visible,
      windowWidth: views.panelWindow.width,
      windowHeight: views.panelWindow.height,
      maximized: views.panelWindow.maximized,
      windowIntegrationStatus: panel.windowIntegrationStatus,
      shortcutState: maintenance.shortcutState,
      shortcutMessage: maintenance.shortcutMessage,
      keysLegendOpen: panel.keysLegendOpen,
      readerLayout: panel.readerLayout,
      inspectorArticleMode: panel.inspectorArticleMode,
      inspectorFactsOpen: panel.inspectorFactsOpen,
      emptyStateMessage: panel.emptyStateMessage(),
      onboardingVisible: session.onboardingVisible,
      homeVisible: panel.homeVisible,
      setupVisible: panel.setupVisible,
      insightDetailVisible: panel.detailItem !== null,
      insightDetailFocusedControl: views.insightDetail.buttons().filter(function(button) { return button.activeFocus }).map(function(button) { return button.controlId || button.label })[0] || "",
      insightDetailControlIds: views.insightDetail.buttons().map(function(button) { return button.controlId || button.label }),
      overviewContentY: views.discoveryView.contentY,
      insightDetailId: panel.detailItem ? String(panel.detailItem.id || "") : "",
      homeCards: views.discoveryView.cards().length,
      selectedHomeKind: views.discoveryView.cards()[views.discoveryView.selectedCard] ? views.discoveryView.cards()[views.discoveryView.selectedCard].entryKind : "",
      insightSourceCount: panel.detailItem ? (panel.detailItem.sourceLinks || []).length : 0,
      insightReviewedAt: panel.detailItem ? String(panel.detailItem.reviewedAt || "") : "",
      selectedHomeCard: views.discoveryView.selectedCard,
      insightsStatus: session.insightsModel.status,
      setupCount: session.setupModel.length,
      relevanceControls: session.relevanceControls,
      openingPhase: windowLifecycle.phase,
      briefing: session.briefing,
      briefingBusy: session.briefingBusy,
      briefingControlsMode: panel.briefingControlsMode,
      briefingControlLabels: controls.map(function(item) { return item.label || "Group updates" }),
      briefingFocusedControl: focusedControl.length ? String(focusedControl[0].label || "Group updates") : "",
      groupExpanded: !!group && group.expanded,
      groupHistoryIndex: group ? group.historyIndex : -1,
      briefingMessage: session.briefingMessage,
      displayedFeedDigest: session.displayedFeedDigest,
      selectedBriefingGroupId: storyViewport.selectedStory ? String(storyViewport.selectedStory.briefingGroupId || "") : "",
      selectedBriefingEventIds: storyViewport.selectedStory && storyViewport.selectedStory.briefingEvents
        ? storyViewport.selectedStory.briefingEvents.map(function(event) { return event.id }) : [],
      selectedBriefingUnreadCount: storyViewport.selectedStory ? Number(storyViewport.selectedStory.briefingUnreadCount || 0) : 0
    })
  }

  function itemGeometry(item, visible) {
    if (!item) return JSON.stringify({ visible: false })
    var point = item.mapToItem(null, 0, 0)
    return JSON.stringify({
      x: point.x,
      y: point.y,
      width: item.width,
      height: item.height,
      visible: visible === undefined ? item.visible : visible
    })
  }

  function sectionRailGeometry() { return views.sectionRail.geometry() }

  function maximizeGeometry() { return itemGeometry(views.masthead.maximizeButton, views.masthead.maximizeButton.visible) }

  function closeGeometry() { return itemGeometry(views.masthead.closeButton, views.masthead.closeButton.visible) }

  function settingsGeometry() {
    return views.keySurface.narrow
      ? itemGeometry(views.readerList.narrowSettingsButton, views.readerList.narrowSettingsButton.visible)
      : itemGeometry(views.readerList.settingsButton, views.readerList.settingsButton.visible)
  }

  function markAllReadGeometry() {
    return views.keySurface.narrow
      ? itemGeometry(views.readerList.narrowMarkAllReadButton, views.readerList.narrowMarkAllReadButton.visible)
      : itemGeometry(views.readerList.markAllReadButton, views.readerList.markAllReadButton.visible)
  }

  function headerUnreadGeometry() {
    return views.keySurface.narrow
      ? itemGeometry(views.readerList.narrowUnreadButton, views.readerList.narrowUnreadButton.visible)
      : itemGeometry(views.readerList.unreadButton, views.readerList.unreadButton.visible)
  }

  function keysLegendGeometry() { return views.sectionRail.keysGeometry() }

  function refreshGeometry() { return itemGeometry(views.masthead.refreshButton, views.masthead.refreshButton.visible) }

  function loadMoreGeometry() {
    return itemGeometry(views.readerList.loadMoreButton, views.readerList.loadMoreButton.visible)
  }

  function filterUnreadGeometry() { return itemGeometry(views.sectionSettings.unreadButton, views.sectionSettings.unreadButton.visible) }

  function filterImagesGeometry() { return itemGeometry(views.sectionSettings.imagesButton, views.sectionSettings.imagesButton.visible) }

  function filterResetGeometry() { return itemGeometry(views.sectionSettings.resetButton, views.sectionSettings.resetButton.visible) }

  function pluginPageGeometry() { return itemGeometry(views.inspectorView.pluginButton, views.inspectorView.pluginButton.visible) }

  function readStateGeometry() {
    return views.keySurface.narrow
      ? itemGeometry(views.readerList.readButton, views.readerList.readButton.visible)
      : itemGeometry(views.inspectorView.readButton, views.inspectorView.readButton.visible)
  }

  function tuneNewspaperGeometry() {
    return itemGeometry(views.preferencesDialog.firstButton, panel.preferencesOpen && views.preferencesDialog.firstButton.visible)
  }

  function shortcutMigrationGeometry() {
    return itemGeometry(views.masthead.shortcutButton, views.masthead.shortcutNotice.visible && views.masthead.shortcutButton.visible)
  }

  function startTodayGeometry() { return itemGeometry(views.welcomeCard.startButton, session.onboardingVisible) }

  function browseStoriesGeometry() { return itemGeometry(views.welcomeCard.browseButton, session.onboardingVisible) }

  function newBriefingGeometry() {
    var notice = panel.homeVisible ? views.discoveryView.notice : views.briefingNotice
    return itemGeometry(notice.newButton, notice.visible)
  }

  function finishBriefingGeometry() {
    var notice = panel.homeVisible ? views.discoveryView.notice : views.briefingNotice
    return itemGeometry(notice.finishButton, notice.visible && notice.finishButton.visible)
  }

  function homeCardGeometry() {
    var cards = views.discoveryView.cards()
    return itemGeometry(cards[views.discoveryView.selectedCard], panel.overviewVisible && cards.length > 0)
  }

  function groupReadGeometry() {
    var group = views.keySurface.narrow ? views.readerList.list.headerItem : views.inspectorView.group
    if (!group) return JSON.stringify({ visible: false })
    return itemGeometry(group.readButton, group.visible && group.readButton.visible)
  }

}
