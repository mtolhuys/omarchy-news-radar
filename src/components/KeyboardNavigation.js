.pragma library

// Return the closest enabled control in the requested visual direction.
// Layout owners retain focus and scrolling decisions; every keyboard surface
// shares this geometry rule so grids and rows behave consistently.
function spatialTarget(controls, surface, horizontal, vertical) {
  if (!controls.length) return null
  var active = controls.findIndex(function(control) { return control.activeFocus })
  if (active < 0) return controls[0]
  var current = controls[active]
  var origin = current.mapToItem(surface, current.width / 2, current.height / 2)
  var best = null
  var bestScore = Number.MAX_VALUE
  for (var i = 0; i < controls.length; i++) {
    if (i === active) continue
    var candidate = controls[i]
    var point = candidate.mapToItem(surface, candidate.width / 2, candidate.height / 2)
    var dx = point.x - origin.x
    var dy = point.y - origin.y
    if ((horizontal < 0 && dx >= 0) || (horizontal > 0 && dx <= 0)
        || (vertical < 0 && dy >= 0) || (vertical > 0 && dy <= 0)) continue
    var primary = horizontal !== 0 ? Math.abs(dx) : Math.abs(dy)
    var secondary = horizontal !== 0 ? Math.abs(dy) : Math.abs(dx)
    var score = primary + secondary * 3
    if (score < bestScore) { best = candidate; bestScore = score }
  }
  return best
}
