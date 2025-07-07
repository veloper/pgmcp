import json
import typing as t

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


options_json_schema_json = """
{
  "title": "Options",
  "type": "object",
  "properties": {
    "autoResize": { "type": "boolean", "default": true, "description": "If true, the Network will automatically detect when its container is resized, and redraw itself accordingly." },
    "height": { "type": "string", "default": "100%", "description": "The height of the canvas. Can be in percentages or pixels (e.g., '400px', '100%')." },
    "width": { "type": "string", "default": "100%", "description": "The width of the canvas. Can be in percentages or pixels (e.g., '400px', '100%')." },
    "locale": { "type": "string", "default": "en", "description": "Select the locale. By default, the language is English." },
    "locales": {
      "type": "object",
      "additionalProperties": {
        "title": "LocaleLabels",
        "type": "object",
        "properties": {
          "edit": { "type": ["string", "null"], "default": "Edit", "description": "Edit label." },
          "del": { "type": ["string", "null"], "default": "Delete selected", "description": "Delete selected label." },
          "back": { "type": ["string", "null"], "default": "Back", "description": "Back label." },
          "addNode": { "type": ["string", "null"], "default": "Add Node", "description": "Add Node label." },
          "addEdge": { "type": ["string", "null"], "default": "Add Edge", "description": "Add Edge label." },
          "editNode": { "type": ["string", "null"], "default": "Edit Node", "description": "Edit Node label." },
          "editEdge": { "type": ["string", "null"], "default": "Edit Edge", "description": "Edit Edge label." },
          "addDescription": { "type": ["string", "null"], "default": "Click in an empty space to place a new node.", "description": "Description for adding a node." },
          "edgeDescription": { "type": ["string", "null"], "default": "Click on a node and drag the edge to another node to connect them.", "description": "Description for adding an edge." },
          "editEdgeDescription": { "type": ["string", "null"], "default": "Click on the control points and drag them to a node to connect.", "description": "Description for editing an edge." },
          "createEdgeError": { "type": ["string", "null"], "default": "Cannot link those nodes.", "description": "Error message for creating an edge." },
          "deleteClusterError": { "type": ["string", "null"], "default": "Cluster cannot be deleted.", "description": "Error message for deleting a cluster." },
          "editClusterError": { "type": ["string", "null"], "default": "Cluster cannot be edited.", "description": "Error message for editing a cluster." }
        },
        "additionalProperties": true
      },
      "description": "Locales object."
    },
    "clickToUse": { "type": "boolean", "default": false, "description": "When true, the network will only react to mouse and touch events when active (clicked)." },
    "configure": {
      "title": "ConfigureOptions",
      "type": "object",
      "properties": {
        "enabled": { "type": ["boolean", "null"], "default": true, "description": "Enable the configurator UI." },
        "filter": {
          "anyOf": [
            { "type": "boolean" },
            { "type": "array", "items": { "type": "string" } }
          ],
          "default": true,
          "description": "Filter which options are shown in the configurator. Can be true (all), or a list of modules."
        },
        "container": { "type": ["string", "null"], "default": null, "description": "DOM selector for the configurator container." },
        "showButton": { "type": ["boolean", "null"], "default": true, "description": "Show the apply button in the configurator." }
      },
      "additionalProperties": true
    },
    "edges": {
      "title": "EdgesOptions",
      "type": "object",
      "properties": {
        "arrows": {
          "anyOf": [
            { "type": "string" },
            {
              "title": "EdgeArrowsObject",
              "type": "object",
              "properties": {
                "to": { "type": ["boolean", "null"], "default": null, "description": "Show arrow at the 'to' end." },
                "from": { "type": ["boolean", "null"], "default": null, "description": "Show arrow at the 'from' end." },
                "middle": { "type": ["boolean", "null"], "default": null, "description": "Show arrow in the middle." }
              },
              "additionalProperties": true
            }
          ],
          "default": null,
          "description": "Arrow settings for edges."
        },
        "color": {
          "anyOf": [
            { "type": "string" },
            {
              "title": "EdgeColorObject",
              "type": "object",
              "properties": {
                "color": { "type": ["string", "null"], "default": null, "description": "Default edge color." },
                "highlight": { "type": ["string", "null"], "default": null, "description": "Color when edge is highlighted." },
                "hover": { "type": ["string", "null"], "default": null, "description": "Color when edge is hovered." },
                "inherit": {
                  "type": ["string", "null"],
                  "enum": ["from", "to", "both", "none"],
                  "default": "from",
                  "description": "Inherit color from node."
                },
                "opacity": { "type": "number", "minimum": 0.0, "maximum": 1.0, "default": 1.0, "description": "Edge opacity (0-1). Should be between 0 and 1." }
              },
              "additionalProperties": true
            }
          ],
          "default": null,
          "description": "Edge color."
        },
        "dashes": { "type": ["boolean", "null"], "default": false, "description": "Draw edge as dashed line." },
        "hidden": { "type": ["boolean", "null"], "default": false, "description": "Hide the edge from view." },
        "hoverWidth": {
          "anyOf": [
            { "type": "number" },
            { "type": "string" }
          ],
          "default": 0.5,
          "description": "Width of edge when hovered."
        },
        "label": { "type": ["string", "null"], "default": null, "description": "Label for the edge." },
        "labelHighlightBold": { "type": ["boolean", "null"], "default": true, "description": "Bold label when selected." },
        "length": { "type": ["number", "null"], "default": null, "description": "Edge length (for layout)." },
        "physics": { "type": ["boolean", "null"], "default": true, "description": "Include edge in physics simulation." },
        "scaling": {
          "title": "EdgeScaling",
          "type": "object",
          "properties": {
            "min": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Minimum width." },
            "max": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Maximum width." },
            "label": {
              "title": "EdgeScalingLabel",
              "type": "object",
              "properties": {
                "enabled": { "type": ["boolean", "null"], "default": null, "description": "Enable label scaling." },
                "min": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Minimum label size." },
                "max": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Maximum label size." },
                "maxVisible": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Maximum visible label size." },
                "drawThreshold": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Draw threshold for label scaling." }
              },
              "additionalProperties": true
            }
          },
          "additionalProperties": true
        },
        "selectionWidth": {
          "anyOf": [
            { "type": "number" },
            { "type": "string" }
          ],
          "default": 1,
          "description": "Width of edge when selected."
        },
        "selfReferenceSize": { "type": ["number", "null"], "default": null, "description": "Size of self-referencing edge loops." },
        "selfReference": { "type": ["object", "null"], "default": null, "description": "Self-reference options for edges." },
        "shadow": { "type": ["boolean", "null"], "default": false, "description": "Draw a shadow under the edge." },
        "smooth": {
          "anyOf": [
            { "type": "boolean" },
            {
              "title": "EdgeSmoothObject",
              "type": "object",
              "properties": {
                "enabled": { "type": "boolean", "default": true, "description": "Enable smooth edges." },
                "type": {
                  "type": "string",
                  "enum": [
                    "dynamic", "continuous", "discrete", "diagonalCross", "straightCross",
                    "horizontal", "vertical", "curvedCW", "curvedCCW", "cubicBezier"
                  ],
                  "default": "dynamic",
                  "description": "Type of smooth curve."
                }
              },
              "additionalProperties": true
            }
          ],
          "default": null,
          "description": "Smooth edge settings."
        },
        "title": { "type": ["string", "null"], "default": null, "description": "Tooltip for the edge." },
        "value": { "type": ["number", "null"], "default": null, "description": "Value for scaling edge width." },
        "width": { "type": ["number", "null"], "default": 1, "description": "Edge width." },
        "widthConstraint": {
          "anyOf": [
            { "type": "number" },
            { "type": "boolean" },
            { "type": "object" }
          ],
          "default": false,
          "description": "Width constraint for the edge label."
        },
        "from": {
          "anyOf": [
            { "type": "string" },
            { "type": "integer" }
          ],
          "default": null,
          "description": "Source node id (per edge only)."
        },
        "to": {
          "anyOf": [
            { "type": "string" },
            { "type": "integer" }
          ],
          "default": null,
          "description": "Target node id (per edge only)."
        },
        "id": { "type": ["string", "null"], "default": null, "description": "Edge id (per edge only)." }
      },
      "additionalProperties": true
    },
    "nodes": {
      "title": "NodesOptions",
      "type": "object",
      "properties": {
        "borderWidth": { "type": "number", "minimum": 0, "default": 1, "description": "Width of the node border." },
        "borderWidthSelected": { "type": "number", "minimum": 0, "default": 2, "description": "Width of the border when selected." },
        "brokenImage": { "type": ["string", "null"], "default": null, "description": "Backup image URL if main image fails." },
        "color": {
          "anyOf": [
            { "type": "string" },
            {
              "title": "NodeColorObject",
              "type": "object",
              "properties": {
                "border": { "type": ["string", "null"], "default": null, "description": "Border color." },
                "background": { "type": ["string", "null"], "default": null, "description": "Background color." },
                "highlight": {
                  "title": "NodeColorHighlight",
                  "type": "object",
                  "properties": {
                    "border": { "type": ["string", "null"], "default": null, "description": "Border color when highlighted." },
                    "background": { "type": ["string", "null"], "default": null, "description": "Background color when highlighted." }
                  },
                  "additionalProperties": true
                },
                "hover": {
                  "title": "NodeColorHover",
                  "type": "object",
                  "properties": {
                    "border": { "type": ["string", "null"], "default": null, "description": "Border color when hovered." },
                    "background": { "type": ["string", "null"], "default": null, "description": "Background color when hovered." }
                  },
                  "additionalProperties": true
                }
              },
              "additionalProperties": true
            }
          ],
          "default": null,
          "description": "Node color."
        },
        "ctxRenderer": {},
        "fixed": {
          "anyOf": [
            { "type": "boolean" },
            {
              "title": "NodeFixedObject",
              "type": "object",
              "properties": {
                "x": { "type": ["boolean", "null"], "default": false, "description": "Fix x position." },
                "y": { "type": ["boolean", "null"], "default": false, "description": "Fix y position." }
              },
              "additionalProperties": true
            }
          ],
          "default": false,
          "description": "Fix node position."
        },
        "font": {
          "anyOf": [
            { "type": "string" },
            {
              "title": "NodeFontObject",
              "type": "object",
              "properties": {
                "color": { "type": ["string", "null"], "default": null, "description": "Font color." },
                "size": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Font size." },
                "face": {
                  "type": ["string", "null"],
                  "enum": ["arial", "FontAwesome", "Ionicons", "MaterialIcons"],
                  "default": null,
                  "description": "Font family."
                },
                "background": { "type": ["string", "null"], "default": null, "description": "Font background color." },
                "strokeWidth": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Font stroke width." },
                "strokeColor": { "type": ["string", "null"], "default": null, "description": "Font stroke color." },
                "align": {
                  "type": ["string", "null"],
                  "enum": ["left", "center", "right"],
                  "default": null,
                  "description": "Font alignment."
                }
              },
              "additionalProperties": true
            }
          ],
          "default": null,
          "description": "Font settings for node label."
        },
        "group": { "type": ["string", "null"], "default": null, "description": "Group name for node styling." },
        "heightConstraint": {
          "anyOf": [
            { "type": "number" },
            { "type": "boolean" },
            { "type": "object" }
          ],
          "default": false,
          "description": "Height constraint for the node."
        },
        "hidden": { "type": ["boolean", "null"], "default": false, "description": "Hide the node from view." },
        "icon": {
          "title": "NodeIcon",
          "type": "object",
          "properties": {
            "face": {
              "type": ["string", "null"],
              "enum": ["arial", "FontAwesome", "Ionicons", "MaterialIcons"],
              "default": null,
              "description": "Font face for the icon."
            },
            "code": { "type": ["integer", "null"], "default": null, "description": "Unicode or icon code." },
            "size": { "type": ["integer", "null"], "minimum": 0, "default": null, "description": "Size of the icon in px." },
            "color": { "type": ["string", "null"], "default": null, "description": "Color of the icon." },
            "weight": {
              "type": ["string", "null"],
              "enum": ["normal", "bold", "100", "200", "300", "400", "500", "600", "700", "800", "900"],
              "default": null,
              "description": "Font weight."
            }
          },
          "additionalProperties": true
        },
        "id": {
          "anyOf": [
            { "type": "string" },
            { "type": "integer" }
          ],
          "default": null,
          "description": "Node id (per node only)."
        },
        "image": { "type": ["string", "null"], "default": null, "description": "Image URL for the node." },
        "imagePadding": {
          "anyOf": [
            { "type": "integer" },
            { "type": "object" }
          ],
          "default": 0,
          "description": "Padding for the image inside the node."
        },
        "label": { "type": ["string", "null"], "default": null, "description": "Label for the node." },
        "labelHighlightBold": { "type": ["boolean", "null"], "default": true, "description": "Bold label when selected." },
        "level": { "type": ["number", "null"], "default": null, "description": "Level for hierarchical layout." },
        "margin": {
          "anyOf": [
            { "type": "integer" },
            { "type": "object" }
          ],
          "default": 5,
          "description": "Margin for the node label."
        },
        "mass": { "type": ["number", "null"], "default": 1, "description": "Node mass for physics simulation." },
        "opacity": { "type": ["number", "null"], "default": null, "description": "Overall opacity of the node." },
        "physics": { "type": ["boolean", "null"], "default": true, "description": "Include node in physics simulation." },
        "scaling": {
          "title": "NodeScaling",
          "type": "object",
          "properties": {
            "min": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Minimum node size." },
            "max": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Maximum node size." },
            "label": { "type": ["boolean", "null"], "default": null, "description": "Scale label with node size." },
            "customScalingFunction": { "type": ["string", "null"], "default": null, "description": "Custom scaling function as a string." }
          },
          "additionalProperties": true
        },
        "shadow": { "type": ["boolean", "null"], "default": false, "description": "Draw a shadow under the node." },
        "shape": {
          "type": "string",
          "enum": [
            "ellipse", "circle", "box", "text", "database", "diamond", "dot", "star",
            "triangle", "triangleDown", "hexagon", "square", "icon", "image", "circularImage"
          ],
          "default": "ellipse",
          "description": "Shape of the node."
        },
        "shapeProperties": {
          "title": "NodeShapeProperties",
          "type": "object",
          "properties": {
            "borderDashes": { "type": ["boolean", "null"], "default": false, "description": "Draw border as dashed line." },
            "borderRadius": { "type": ["number", "null"], "default": 6, "description": "Border radius for box/rect shapes." },
            "interpolation": { "type": ["boolean", "null"], "default": true, "description": "Interpolate image for image/circularImage shapes." },
            "useImageSize": { "type": ["boolean", "null"], "default": false, "description": "Use image size for image/circularImage shapes." },
            "useBorderWithImage": { "type": ["boolean", "null"], "default": false, "description": "Draw border with image shapes." }
          },
          "additionalProperties": true
        },
        "size": { "type": "number", "minimum": 0, "default": 25, "description": "Node size." },
        "title": { "type": ["string", "null"], "default": null, "description": "Tooltip for the node." },
        "value": { "type": ["number", "null"], "default": null, "description": "Value for scaling node size." },
        "widthConstraint": {
          "anyOf": [
            { "type": "number" },
            { "type": "boolean" },
            { "type": "object" }
          ],
          "default": false,
          "description": "Width constraint for the node."
        },
        "x": { "type": ["number", "null"], "default": null, "description": "Initial x position." },
        "y": { "type": ["number", "null"], "default": null, "description": "Initial y position." }
      },
      "additionalProperties": true
    },
    "groups": {
      "type": "object",
      "additionalProperties": {
        "title": "NodesOptions",
        "type": "object",
        "properties": {
          "borderWidth": { "type": "number", "minimum": 0, "default": 1, "description": "Width of the node border." },
          "borderWidthSelected": { "type": "number", "minimum": 0, "default": 2, "description": "Width of the border when selected." },
          "brokenImage": { "type": ["string", "null"], "default": null, "description": "Backup image URL if main image fails." },
          "color": {
            "anyOf": [
              { "type": "string" },
              {
                "title": "NodeColorObject",
                "type": "object",
                "properties": {
                  "border": { "type": ["string", "null"], "default": null, "description": "Border color." },
                  "background": { "type": ["string", "null"], "default": null, "description": "Background color." },
                  "highlight": {
                    "title": "NodeColorHighlight",
                    "type": "object",
                    "properties": {
                      "border": { "type": ["string", "null"], "default": null, "description": "Border color when highlighted." },
                      "background": { "type": ["string", "null"], "default": null, "description": "Background color when highlighted." }
                    },
                    "additionalProperties": true
                  },
                  "hover": {
                    "title": "NodeColorHover",
                    "type": "object",
                    "properties": {
                      "border": { "type": ["string", "null"], "default": null, "description": "Border color when hovered." },
                      "background": { "type": ["string", "null"], "default": null, "description": "Background color when hovered." }
                    },
                    "additionalProperties": true
                  }
                },
                "additionalProperties": true
              }
            ],
            "default": null,
            "description": "Node color."
          },
          "ctxRenderer": {},
          "fixed": {
            "anyOf": [
              { "type": "boolean" },
              {
                "title": "NodeFixedObject",
                "type": "object",
                "properties": {
                  "x": { "type": ["boolean", "null"], "default": false, "description": "Fix x position." },
                  "y": { "type": ["boolean", "null"], "default": false, "description": "Fix y position." }
                },
                "additionalProperties": true
              }
            ],
            "default": false,
            "description": "Fix node position."
          },
          "font": {
            "anyOf": [
              { "type": "string" },
              {
                "title": "NodeFontObject",
                "type": "object",
                "properties": {
                  "color": { "type": ["string", "null"], "default": null, "description": "Font color." },
                  "size": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Font size." },
                  "face": {
                    "type": ["string", "null"],
                    "enum": ["arial", "FontAwesome", "Ionicons", "MaterialIcons"],
                    "default": null,
                    "description": "Font family."
                  },
                  "background": { "type": ["string", "null"], "default": null, "description": "Font background color." },
                  "strokeWidth": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Font stroke width." },
                  "strokeColor": { "type": ["string", "null"], "default": null, "description": "Font stroke color." },
                  "align": {
                    "type": ["string", "null"],
                    "enum": ["left", "center", "right"],
                    "default": null,
                    "description": "Font alignment."
                  }
                },
                "additionalProperties": true
              }
            ],
            "default": null,
            "description": "Font settings for node label."
          },
          "group": { "type": ["string", "null"], "default": null, "description": "Group name for node styling." },
          "heightConstraint": {
            "anyOf": [
              { "type": "number" },
              { "type": "boolean" },
              { "type": "object" }
            ],
            "default": false,
            "description": "Height constraint for the node."
          },
          "hidden": { "type": ["boolean", "null"], "default": false, "description": "Hide the node from view." },
          "icon": {
            "title": "NodeIcon",
            "type": "object",
            "properties": {
              "face": {
                "type": ["string", "null"],
                "enum": ["arial", "FontAwesome", "Ionicons", "MaterialIcons"],
                "default": null,
                "description": "Font face for the icon."
              },
              "code": { "type": ["integer", "null"], "default": null, "description": "Unicode or icon code." },
              "size": { "type": ["integer", "null"], "minimum": 0, "default": null, "description": "Size of the icon in px." },
              "color": { "type": ["string", "null"], "default": null, "description": "Color of the icon." },
              "weight": {
                "type": ["string", "null"],
                "enum": ["normal", "bold", "100", "200", "300", "400", "500", "600", "700", "800", "900"],
                "default": null,
                "description": "Font weight."
              }
            },
            "additionalProperties": true
          },
          "id": {
            "anyOf": [
              { "type": "string" },
              { "type": "integer" }
            ],
            "default": null,
            "description": "Node id (per node only)."
          },
          "image": { "type": ["string", "null"], "default": null, "description": "Image URL for the node." },
          "imagePadding": {
            "anyOf": [
              { "type": "integer" },
              { "type": "object" }
            ],
            "default": 0,
            "description": "Padding for the image inside the node."
          },
          "label": { "type": ["string", "null"], "default": null, "description": "Label for the node." },
          "labelHighlightBold": { "type": ["boolean", "null"], "default": true, "description": "Bold label when selected." },
          "level": { "type": ["number", "null"], "default": null, "description": "Level for hierarchical layout." },
          "margin": {
            "anyOf": [
              { "type": "integer" },
              { "type": "object" }
            ],
            "default": 5,
            "description": "Margin for the node label."
          },
          "mass": { "type": ["number", "null"], "default": 1, "description": "Node mass for physics simulation." },
          "opacity": { "type": ["number", "null"], "default": null, "description": "Overall opacity of the node." },
          "physics": { "type": ["boolean", "null"], "default": true, "description": "Include node in physics simulation." },
          "scaling": {
            "title": "NodeScaling",
            "type": "object",
            "properties": {
              "min": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Minimum node size." },
              "max": { "type": ["number", "null"], "minimum": 0, "default": null, "description": "Maximum node size." },
              "label": { "type": ["boolean", "null"], "default": null, "description": "Scale label with node size." },
              "customScalingFunction": { "type": ["string", "null"], "default": null, "description": "Custom scaling function as a string." }
            },
            "additionalProperties": true
          },
          "shadow": { "type": ["boolean", "null"], "default": false, "description": "Draw a shadow under the node." },
          "shape": {
            "type": "string",
            "enum": [
              "ellipse", "circle", "box", "text", "database", "diamond", "dot", "star",
              "triangle", "triangleDown", "hexagon", "square", "icon", "image", "circularImage"
            ],
            "default": "ellipse",
            "description": "Shape of the node."
          },
          "shapeProperties": {
            "title": "NodeShapeProperties",
            "type": "object",
            "properties": {
              "borderDashes": { "type": ["boolean", "null"], "default": false, "description": "Draw border as dashed line." },
              "borderRadius": { "type": ["number", "null"], "default": 6, "description": "Border radius for box/rect shapes." },
              "interpolation": { "type": ["boolean", "null"], "default": true, "description": "Interpolate image for image/circularImage shapes." },
              "useImageSize": { "type": ["boolean", "null"], "default": false, "description": "Use image size for image/circularImage shapes." },
              "useBorderWithImage": { "type": ["boolean", "null"], "default": false, "description": "Draw border with image shapes." }
            },
            "additionalProperties": true
          },
          "size": { "type": "number", "minimum": 0, "default": 25, "description": "Node size." },
          "title": { "type": ["string", "null"], "default": null, "description": "Tooltip for the node." },
          "value": { "type": ["number", "null"], "default": null, "description": "Value for scaling node size." },
          "widthConstraint": {
            "anyOf": [
              { "type": "number" },
              { "type": "boolean" },
              { "type": "object" }
            ],
            "default": false,
            "description": "Width constraint for the node."
          },
          "x": { "type": ["number", "null"], "default": null, "description": "Initial x position." },
          "y": { "type": ["number", "null"], "default": null, "description": "Initial y position." }
        },
        "additionalProperties": true
      },
      "description": "Group definitions for node styling."
    },
    "layout": {
      "title": "LayoutOptions",
      "type": "object",
      "properties": {
        "randomSeed": {
          "anyOf": [
            { "type": "number" },
            { "type": "string" }
          ],
          "default": null,
          "description": "Seed for random layout."
        },
        "improvedLayout": { "type": ["boolean", "null"], "default": true, "description": "Use improved layout algorithm." },
        "clusterThreshold": { "type": ["integer", "null"], "default": 150, "description": "Cluster threshold for improved layout." },
        "hierarchical": {
          "anyOf": [
            { "type": "boolean" },
            {
              "title": "LayoutHierarchicalObject",
              "type": "object",
              "properties": {
                "enabled": { "type": ["boolean", "null"], "default": false, "description": "Enable hierarchical layout." },
                "levelSeparation": { "type": ["number", "null"], "default": 150, "description": "Separation between levels." },
                "nodeSpacing": { "type": ["number", "null"], "default": 100, "description": "Spacing between nodes." },
                "treeSpacing": { "type": ["number", "null"], "default": 200, "description": "Spacing between trees." },
                "blockShifting": { "type": ["boolean", "null"], "default": true, "description": "Enable block shifting." },
                "edgeMinimization": { "type": ["boolean", "null"], "default": true, "description": "Enable edge minimization." },
                "parentCentralization": { "type": ["boolean", "null"], "default": true, "description": "Enable parent centralization." },
                "direction": {
                  "type": "string",
                  "enum": ["UD", "DU", "LR", "RL"],
                  "default": "UD",
                  "description": "Direction of layout."
                },
                "sortMethod": {
                  "type": "string",
                  "enum": ["hubsize", "directed"],
                  "default": "hubsize",
                  "description": "Sorting method for nodes."
                },
                "shakeTowards": {
                  "type": "string",
                  "enum": ["leaves", "roots"],
                  "default": "leaves",
                  "description": "Shake towards direction."
                }
              },
              "additionalProperties": true
            }
          ],
          "default": null,
          "description": "Hierarchical layout options."
        }
      },
      "additionalProperties": true
    },
    "interaction": {
      "title": "InteractionOptions",
      "type": "object",
      "properties": {
        "dragNodes": { "type": ["boolean", "null"], "default": true, "description": "Allow dragging nodes." },
        "dragView": { "type": ["boolean", "null"], "default": true, "description": "Allow dragging the view." },
        "hideEdgesOnDrag": { "type": ["boolean", "null"], "default": false, "description": "Hide edges while dragging." },
        "hideEdgesOnZoom": { "type": ["boolean", "null"], "default": false, "description": "Hide edges while zooming." },
        "hideNodesOnDrag": { "type": ["boolean", "null"], "default": false, "description": "Hide nodes while dragging." },
        "hover": { "type": ["boolean", "null"], "default": false, "description": "Enable hover events." },
        "hoverConnectedEdges": { "type": ["boolean", "null"], "default": true, "description": "Highlight connected edges on hover." },
        "keyboard": {
          "anyOf": [
            { "type": "boolean" },
            {
              "title": "InteractionKeyboardOptions",
              "type": "object",
              "properties": {
                "enabled": { "type": ["boolean", "null"], "default": false, "description": "Enable keyboard navigation." },
                "speed": {
                  "type": ["object", "null"],
                  "additionalProperties": { "type": "integer" },
                  "default": null,
                  "description": "Speed settings for keyboard navigation."
                },
                "bindToWindow": { "type": ["boolean", "null"], "default": true, "description": "Bind keyboard events to window." }
              },
              "additionalProperties": true
            }
          ],
          "default": false,
          "description": "Keyboard navigation options."
        },
        "multiselect": { "type": ["boolean", "null"], "default": false, "description": "Enable multi-selection." },
        "navigationButtons": { "type": ["boolean", "null"], "default": false, "description": "Show navigation buttons." },
        "selectable": { "type": ["boolean", "null"], "default": true, "description": "Allow selection of nodes/edges." },
        "selectConnectedEdges": { "type": ["boolean", "null"], "default": true, "description": "Select connected edges when node is selected." },
        "tooltipDelay": { "type": ["number", "null"], "default": 300, "description": "Delay before showing tooltip (ms)." },
        "zoomSpeed": { "type": ["number", "null"], "default": 1, "description": "Zoom speed." },
        "zoomView": { "type": ["boolean", "null"], "default": true, "description": "Allow zooming the view." }
      },
      "additionalProperties": true
    },
    "manipulation": {
      "title": "ManipulationOptions",
      "type": "object",
      "properties": {
        "enabled": { "type": ["boolean", "null"], "default": false, "description": "Enable manipulation UI." },
        "initiallyActive": { "type": ["boolean", "null"], "default": true, "description": "Start with manipulation active." },
        "addNode": {},
        "addEdge": {},
        "editNode": {},
        "editEdge": {},
        "deleteNode": {},
        "deleteEdge": {},
        "controlNodeStyle": {
          "type": ["object", "null"],
          "default": {
            "shape": "dot",
            "size": 6,
            "color": {
              "background": "#ff0000",
              "border": "#3c3c3c",
              "highlight": {
                "background": "#07f968",
                "border": "#3c3c3c"
              }
            },
            "borderWidth": 2,
            "borderWidthSelected": 2
          },
          "description": "Style for control nodes."
        }
      },
      "additionalProperties": true
    },
    "physics": {
      "title": "PhysicsOptions",
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": true, "description": "Enable physics simulation." },
        "barnesHut": {
          "title": "PhysicsBarnesHut",
          "type": "object",
          "properties": {
            "theta": { "type": ["number", "null"], "minimum": 0, "default": 0.5, "description": "Barnes-Hut theta parameter." },
            "gravitationalConstant": { "type": ["number", "null"], "default": -2000, "description": "Gravitational constant." },
            "centralGravity": { "type": ["number", "null"], "default": 0.3, "description": "Central gravity." },
            "springLength": { "type": ["number", "null"], "default": 95, "description": "Spring length." },
            "springConstant": { "type": ["number", "null"], "default": 0.04, "description": "Spring constant." },
            "damping": { "type": ["number", "null"], "minimum": 0, "maximum": 1, "default": 0.09, "description": "Damping factor." },
            "avoidOverlap": { "type": ["number", "null"], "minimum": 0, "default": 0, "description": "Avoid overlap factor." }
          },
          "additionalProperties": true
        },
        "forceAtlas2Based": {
          "title": "PhysicsForceAtlas2Based",
          "type": "object",
          "properties": {
            "theta": { "type": ["number", "null"], "minimum": 0, "default": 0.5, "description": "ForceAtlas2 theta parameter." },
            "gravitationalConstant": { "type": ["number", "null"], "default": -50, "description": "Gravitational constant." },
            "centralGravity": { "type": ["number", "null"], "default": 0.01, "description": "Central gravity." },
            "springLength": { "type": ["number", "null"], "default": 100, "description": "Spring length." },
            "springConstant": { "type": ["number", "null"], "default": 0.08, "description": "Spring constant." },
            "damping": { "type": ["number", "null"], "minimum": 0, "maximum": 1, "default": 0.4, "description": "Damping factor." },
            "avoidOverlap": { "type": ["number", "null"], "minimum": 0, "default": 0, "description": "Avoid overlap factor." }
          },
          "additionalProperties": true
        },
        "repulsion": {
          "title": "PhysicsRepulsion",
          "type": "object",
          "properties": {
            "centralGravity": { "type": ["number", "null"], "default": 0.2, "description": "Central gravity." },
            "springLength": { "type": ["number", "null"], "default": 200, "description": "Spring length." },
            "springConstant": { "type": ["number", "null"], "default": 0.05, "description": "Spring constant." },
            "nodeDistance": { "type": ["number", "null"], "default": 100, "description": "Node distance." },
            "damping": { "type": ["number", "null"], "minimum": 0, "maximum": 1, "default": 0.09, "description": "Damping factor." }
          },
          "additionalProperties": true
        },
        "hierarchicalRepulsion": {
          "title": "PhysicsHierarchicalRepulsion",
          "type": "object",
          "properties": {
            "centralGravity": { "type": ["number", "null"], "default": 0.0, "description": "Central gravity." },
            "springLength": { "type": ["number", "null"], "default": 100, "description": "Spring length." },
            "springConstant": { "type": ["number", "null"], "default": 0.01, "description": "Spring constant." },
            "nodeDistance": { "type": ["number", "null"], "default": 120, "description": "Node distance." },
            "damping": { "type": ["number", "null"], "minimum": 0, "maximum": 1, "default": 0.09, "description": "Damping factor." },
            "avoidOverlap": { "type": ["number", "null"], "minimum": 0, "default": 0, "description": "Avoid overlap factor." }
          },
          "additionalProperties": true
        },
        "maxVelocity": { "type": ["number", "null"], "default": 50, "description": "Maximum velocity of nodes." },
        "minVelocity": { "type": ["number", "null"], "default": 0.1, "description": "Minimum velocity of nodes." },
        "solver": {
          "type": "string",
          "enum": ["barnesHut", "repulsion", "hierarchicalRepulsion", "forceAtlas2Based"],
          "default": "barnesHut",
          "description": "Physics solver to use."
        },
        "stabilization": {
          "title": "PhysicsStabilization",
          "type": "object",
          "properties": {
            "enabled": { "type": ["boolean", "null"], "default": true, "description": "Enable stabilization." },
            "iterations": { "type": ["integer", "null"], "default": 1000, "description": "Number of stabilization iterations." },
            "updateInterval": { "type": ["integer", "null"], "default": 50, "description": "Update interval in ms." },
            "onlyDynamicEdges": { "type": ["boolean", "null"], "default": false, "description": "Only dynamic edges." },
            "fit": { "type": ["boolean", "null"], "default": true, "description": "Fit after stabilization." }
          },
          "additionalProperties": true
        },
        "timestep": { "type": ["number", "null"], "default": 0.5, "description": "Simulation timestep." },
        "adaptiveTimestep": { "type": ["boolean", "null"], "default": true, "description": "Enable adaptive timestep." },
        "wind": { "type": ["object", "null"], "default": null, "description": "Wind force options." }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true
}
"""
options_json_schema_extra = json.loads(options_json_schema_json)
