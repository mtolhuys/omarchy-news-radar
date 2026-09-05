import QtQuick
import qs.Commons
import "../Model.js" as RadarModel

// Both reader layouts use this escaped, source-linked body. Feed markup is
// never passed to RichText; only locally built validated segments reach it.
Text {
  id: root
  property var story: null
  readonly property bool articleMode: RadarModel.isReaderArticle(story)
  readonly property var segments: !story ? []
    : story.summarySegments && story.summarySegments.length
      ? story.summarySegments : RadarModel.articleSegments(String(story.summary || ""))
  readonly property string plainText: !story ? ""
    : articleMode ? RadarModel.articlePlainText(segments) : String(story.summary || "")
  signal sourceRequested(string url)

  text: !story ? "" : articleMode
    ? RadarModel.articleBodyHtml(segments, Color.accent) : plainText
  textFormat: root.articleMode ? Text.RichText : Text.PlainText
  color: Color.popups.text
  linkColor: Color.accent
  font.family: Style.font.family
  font.pixelSize: Style.font.body
  lineHeight: 1.28
  wrapMode: Text.WordWrap
  Accessible.role: Accessible.StaticText
  Accessible.name: plainText
  onLinkActivated: function(link) { root.sourceRequested(link) }

  HoverHandler {
    enabled: root.hoveredLink && root.hoveredLink.length > 0
    cursorShape: Qt.PointingHandCursor
  }
}
