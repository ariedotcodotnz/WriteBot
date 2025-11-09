/*!
 * vanilla js ruler
 * Kenneth D'silva (Modracx), Copyright (c) October 2025
 * Licensed under the MIT License – https://opensource.org/licenses/MIT
 */
(function () {
    function pixelsPerInch() {
        const div = document.createElement("div");
        div.style.width = "1in";
        div.style.position = "absolute";
        div.style.visibility = "hidden";
        document.body.appendChild(div);
        const ppi = div.offsetWidth;
        document.body.removeChild(div);
        return ppi;
      }

      function pixelsPerUnit(unit = "px") {
        const ppi = pixelsPerInch();
        switch (unit) {
          case "in":
            return ppi;
          case "cm":
            return ppi / 2.54;
          case "mm":
            return ppi / 25.4;
          case "px":
          default:
            return 1;
        }
      }

      function unitToPixels(value, unit) {
        return value * pixelsPerUnit(unit);
      }

      function pixelsToUnits(px, unit) {
        return px / pixelsPerUnit(unit);
      }

      function createElement(tag, style = {}) {
        const el = document.createElement(tag);
        Object.assign(el.style, style);
        return el;
      }

      function createRuler(container, options = {}) {
        if (container.__rulerCleanup) {
          container.__rulerCleanup();
          delete container.__rulerCleanup;
        }

        const defaults = {
          vRuleSize: 18,
          hRuleSize: 18,
          showCrosshair: true,
          showMousePos: true,
          tickColor: "#323232",
          crosshairColor: "#000",
          crosshairStyle: "dotted",
          mouseBoxBg: "#323232",
          mouseBoxColor: "#fff",
          unit: "in",
          unitPrecision: 1,
        };

        const settings = Object.assign(defaults, options);
        const pxPerUnit = pixelsPerUnit(settings.unit);

        const hRule = createElement("div", {
          position: "absolute",
          background: "#e5e5e5",
          height: settings.hRuleSize + "px",
          width: "100%",
          top: "0",
          left: "0",
          borderBottom: "1px solid #ccc",
          zIndex: "9",
          fontSize: "12px",
          color: "#323232",
          overflow: "hidden",
          pointerEvents: "none",
          lineHeight: "14px",
          userSelect: "none",
        });

        const vRule = createElement("div", {
          position: "absolute",
          background: "#e5e5e5",
          width: settings.vRuleSize + "px",
          height: "100%",
          top: "0",
          left: "0",
          borderRight: "1px solid #ccc",
          zIndex: "9",
          fontSize: "12px",
          color: "#323232",
          overflow: "hidden",
          pointerEvents: "none",
          lineHeight: "14px",
          userSelect: "none",
        });

        const corner = createElement("div", {
          position: "absolute",
          width: settings.vRuleSize + "px",
          height: settings.hRuleSize + "px",
          background: "#e5e5e5",
          top: "0",
          left: "0",
          borderRight: "1px solid #ccc",
          borderBottom: "1px solid #ccc",
          zIndex: "10",
        });

        container.appendChild(hRule);
        container.appendChild(vRule);
        container.appendChild(corner);

        let vMouse, hMouse, mousePosBox;

        if (settings.showCrosshair) {
          vMouse = createElement("div", {
            position: "absolute",
            width: "100%",
            height: "0px",
            left: "0",
            borderBottom: `1px ${settings.crosshairStyle} ${settings.crosshairColor}`,
            zIndex: "11",
            pointerEvents: "none",
          });
          hMouse = createElement("div", {
            position: "absolute",
            height: "100%",
            width: "0px",
            top: "0",
            borderLeft: `1px ${settings.crosshairStyle} ${settings.crosshairColor}`,
            zIndex: "11",
            pointerEvents: "none",
          });
          container.appendChild(vMouse);
          container.appendChild(hMouse);
        }

        if (settings.showMousePos) {
          mousePosBox = createElement("div", {
            position: "absolute",
            fontSize: "12px",
            background: settings.mouseBoxBg,
            color: settings.mouseBoxColor,
            whiteSpace: "nowrap",
            zIndex: "12",
            pointerEvents: "none",
            padding: "3px 10px",
            borderRadius: "5px",
            boxShadow: "2px 2px 5px rgba(0, 0, 0, 0.4)",
          });
          container.appendChild(mousePosBox);
        }

        function getTickType(unitValue) {
          const u = settings.unit;
          if (u === "in" || u === "cm") {
            const frac = unitValue % 1;
            if (Math.abs(frac) < 0.001) return "major";
            if (Math.abs(frac - 0.5) < 0.001) return "medium";
            return "small";
          } else if (u === "mm") {
            const mod = unitValue % 10;
            if (mod === 0) return "major";
            if (mod === 5) return "medium";
            return "small";
          } else if (u === "px") {
            const mod = unitValue % 100;
            if (mod === 0) return "major";
            if (mod === 50) return "medium";
            return "small";
          }
          return "small";
        }

        function renderTicks() {
          hRule.innerHTML = "";
          vRule.innerHTML = "";
          vRule.style.height = container.offsetHeight + "px";

          const hMax = hRule.offsetWidth;
          const totalHUnits = pixelsToUnits(
            hMax - settings.vRuleSize,
            settings.unit
          );
          const step = settings.unit === "px" ? 10 : settings.unit === "mm" ? 1 : 0.1;

          for (let i = 0; i <= totalHUnits / step; i++) {
            const unitValue = i * step;
            const tickType = getTickType(unitValue);
            const tickPx =
              settings.vRuleSize + unitToPixels(unitValue, settings.unit);

            let tickHeight =
              tickType === "small"
                ? "4px"
                : tickType === "medium"
                ? "6px"
                : "100%";

            const tick = createElement("div", {
              position: "absolute",
              bottom: "0",
              left: tickPx + "px",
              width: "1px",
              background: settings.tickColor,
              height: tickHeight,
            });

            if (tickType === "major") {
              const label = createElement("span", {
                position: "absolute",
                top: "2px",
                left: "4px",
                fontSize: "10px",
                color: settings.tickColor,
              });
              label.textContent =
                unitValue.toFixed(settings.unitPrecision);
              tick.appendChild(label);
            }
            hRule.appendChild(tick);
          }

          const vMax = vRule.offsetHeight;
          const totalVUnits = pixelsToUnits(
            vMax - settings.hRuleSize,
            settings.unit
          );
          for (let i = 0; i <= totalVUnits / step; i++) {
            const unitValue = i * step;
            const tickType = getTickType(unitValue);
            const tickPx =
              settings.hRuleSize + unitToPixels(unitValue, settings.unit);

            let tickWidth =
              tickType === "small"
                ? "4px"
                : tickType === "medium"
                ? "6px"
                : "100%";

            const tick = createElement("div", {
              position: "absolute",
              top: tickPx + "px",
              right: "0",
              height: "1px",
              background: settings.tickColor,
              width: tickWidth,
            });

            if (tickType === "major" && unitValue > 0) {
              const label = createElement("span", {
                display: "block",
                position: "absolute",
                top: "4px",
                left: "50%",
                transform: "translateX(-50%) rotate(-90deg)",
                transformOrigin: "top center",
                color: settings.tickColor,
                fontSize: "10px",
              });
              label.textContent =
                unitValue.toFixed(settings.unitPrecision);
              tick.appendChild(label);
            }
            vRule.appendChild(tick);
          }
        }

        function onMouseMove(e) {
          const rect = container.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;

          if (settings.showCrosshair) {
            vMouse.style.top = y + "px";
            hMouse.style.left = x + "px";
          }

          if (settings.showMousePos) {
            const xVal = pixelsToUnits(
              x - settings.vRuleSize,
              settings.unit
            ).toFixed(settings.unitPrecision);
            const yVal = pixelsToUnits(
              y - settings.hRuleSize,
              settings.unit
            ).toFixed(settings.unitPrecision);
            mousePosBox.innerHTML = `x: ${xVal} ${settings.unit}<br>y: ${yVal} ${settings.unit}`;
            mousePosBox.style.top = y + 16 + "px";
            mousePosBox.style.left = x + 12 + "px";
          }
        }

        renderTicks();
        window.addEventListener("resize", renderTicks);
        container.addEventListener("mousemove", onMouseMove);

        container.__rulerCleanup = function () {
          [hRule, vRule, corner, vMouse, hMouse, mousePosBox].forEach(
            (el) => el && el.remove()
          );
          container.removeEventListener("mousemove", onMouseMove);
          window.removeEventListener("resize", renderTicks);
        };
      }

      function clearRuler(container) {
        if (container.__rulerCleanup) {
          container.__rulerCleanup();
          delete container.__rulerCleanup;
        }
      }
      window.Ruler = {
        create: createRuler,
        clear: clearRuler,
      };
})();