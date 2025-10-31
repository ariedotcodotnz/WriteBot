# **ruler-js**

**`ruler-js`** is a lightweight, customizable on-screen **ruler and measurement tool** for web pages.  
It displays **horizontal and vertical rulers**, supports multiple **measurement units**, and provides an optional **crosshair** and **mouse position indicator** for precise layout inspection.

This library is available in both **vanilla JavaScript** and **jQuery** versions, making it easy to integrate into any project or web application.

---

## Key Features

- Horizontal & vertical rulers for measurement overlays
- Supports **inches (in)**, **centimeters (cm)**, **millimeters (mm)**, and **pixels (px)**
- Optional **crosshair** and **mouse position box** for interactive feedback
- Fully customizable appearance and precision
- Auto-adjusts on window resize
- Easy initialization and cleanup via simple API
- Works standalone or as a **jQuery plugin**

---

## Configurable Options (with Defaults)

| Option           | Default     | Description                                           |
| ---------------- | ----------- | ----------------------------------------------------- |
| `vRuleSize`      | `18`        | Width (in px) of the vertical ruler                   |
| `hRuleSize`      | `18`        | Height (in px) of the horizontal ruler                |
| `showCrosshair`  | `true`      | Whether to show the crosshair lines                   |
| `showMousePos`   | `true`      | Whether to show the floating mouse position box       |
| `tickColor`      | `"#323232"` | Color of the tick marks                               |
| `crosshairColor` | `"#000"`    | Color of the crosshair lines                          |
| `crosshairStyle` | `"dotted"`  | Line style of the crosshair (`solid`, `dotted`, etc.) |
| `mouseBoxBg`     | `"#323232"` | Background color of the mouse position box            |
| `mouseBoxColor`  | `"#fff"`    | Text color of the mouse position box                  |
| `unit`           | `"in"`      | Measurement unit (`in`, `cm`, `mm`, `px`)             |
| `unitPrecision`  | `1`         | Decimal precision for displayed measurements          |

---

## Example Usage

### **Vanilla JavaScript**

```js
const container = document.getElementById("rulerContainer");
// Create ruler
Ruler.create(container, {
  unit: "in",
  unitPrecision: 1,
  crosshairColor: "red",
  crosshairStyle: "dashed",
  mouseBoxBg: "#444",
  mouseBoxColor: "white",
  tickColor: "#000",
});

// Clear ruler
Ruler.clear(container);
```

### **jQuery**

```js
const $el = $("#rulerContainer");
// Create ruler
$el.Ruler("create", {
  unit: "in",
  unitPrecision: 1,
  crosshairColor: "red",
  crosshairStyle: "dashed",
  mouseBoxBg: "#444",
  mouseBoxColor: "white",
  tickColor: "#000",
});

// Clear ruler
$el.Ruler("clear");
```

### Note:

> The ruler relies on browser-calculated DPI to approximate real-world units.
Actual pixel-per-inch (PPI) measurements may vary slightly depending on the display and browser scaling.