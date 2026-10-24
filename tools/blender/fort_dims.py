"""Dimensions of the Castillo de San Marcos, measured from the HABS FL-17 drawings.

Sources (Library of Congress, https://www.loc.gov/item/fl0095/; fetch with tools/fetch_habs.py):
  sheet 12  1987 terreplein floor plan (bastion faces/flanks, curtains, court, moat, ravelin)
  sheet 17  1987 sections A-A, east and west casemates (wall thickness, levels)
  sheets 18-21  1987 east/south/west/north elevations (heights, embrasures, garitas, tower)
  sheet 5   1936 elevations and main (bell) tower details

The plan drawing has east at the top and south to the right. Here, as in the game:
+X is east, +Z is south, Y is up, metres, origin at the centre of the court, y = 0 at the
moat floor. Plan values are the exterior lines at parapet level unless noted.
"""

FT = 0.3048


def ft(feet: float, inches: float = 0.0) -> float:
    return (feet + inches / 12.0) * FT


# --- Court (Plaza de Armas), sheet 12 ---------------------------------------------------
# East side 109'-10 1/2", west side 117'-8 1/2", north 108'-3 3/4", south 108'-0 3/4".
# Modelled as a rectangle with the average sizes.
COURT_X = ft(108, 2.25)                       # east-west extent (north/south sides)
COURT_Z = (ft(109, 10.5) + ft(117, 8.5)) / 2  # north-south extent (east/west sides)

# --- Ring of casemates: court wall to the curtain's exterior line at parapet level -------
# Scaled from sheet 12 (about 4.4 px/ft on the 1600 px crop).
RING_EAST = 12.1
RING_WEST = 13.1
RING_NORTH = 12.4
RING_SOUTH = 12.1

# --- Curtains: length between the flanks, sheet 12 ---------------------------------------
CURTAIN_EAST = ft(138, 0.5)
CURTAIN_WEST = ft(154, 2.5)
CURTAIN_NORTH = ft(139, 7)
CURTAIN_SOUTH = ft(139, 4)

# --- Bastions: flank and face lengths, sheet 12 ------------------------------------------
# Each bastion: the flank on the east/west curtain, the flank on the north/south curtain,
# the face toward east/west, the face toward north/south.
BASTIONS = {
    # NE, with the main watch (bell) tower at the salient
    "San Carlos": {"corner": (1, -1), "flank_ew": ft(31, 4.25), "flank_ns": ft(31, 5),
                   "face_ew": ft(85, 8), "face_ns": ft(87, 1.5), "tower": "bell"},
    # SE
    "San Agustin": {"corner": (1, 1), "flank_ew": ft(31, 9.5), "flank_ns": ft(30, 0),
                    "face_ew": ft(86, 3), "face_ns": ft(85, 5), "tower": "garita"},
    # SW
    "San Pedro": {"corner": (-1, 1), "flank_ew": ft(31, 0.5), "flank_ns": ft(30, 11.5),
                  "face_ew": ft(79, 8), "face_ns": ft(79, 1), "tower": "garita"},
    # NW
    "San Pablo": {"corner": (-1, -1), "flank_ew": ft(31, 9.75), "flank_ns": ft(31, 3.75),
                  "face_ew": ft(77, 7), "face_ns": ft(78, 0), "tower": "garita"},
}

# --- Heights above the moat floor, sheets 18-21 ------------------------------------------
# South elevation: 23'-1" scarp + 2'-8" cordon + 10'-3" parapet = 36'-0" overall;
# north elevation: 25'-7 1/4" scarp. A 1738 rebuild raised the walls to about 33-35 ft.
SCARP_TOP = ft(24, 0)           # top of the sloped scarp, where the cordon starts
CORDON_HEIGHT = ft(2, 8)
PARAPET_TOP = ft(35, 0)
# The scarp leans back about 1 in 5.5 (scaled from the elevations and sections).
SCARP_BATTER = 1.0 / 5.5
CORDON_PROJECTION = 0.28
# Gun deck (terreplein) level, and the parapet: 9 ft thick at the top (NPS: walls 14-19 ft at
# the base tapering to 9 ft at the top).
TERREPLEIN = PARAPET_TOP - 2.0
PARAPET_THICKNESS = ft(9, 0)
# Embrasures: about 5'-1" wide (south elevation), cut down to sill height above the deck.
EMBRASURE_INNER_WIDTH = ft(4, 0)
EMBRASURE_OUTER_WIDTH = ft(6, 6)
EMBRASURE_SILL = TERREPLEIN + 0.85

# Grade around the fort and the floor of the court, above the moat floor (sheet 17).
GRADE = 2.0
COURT_FLOOR = 2.1

# --- Moat, counterscarp and ravelin, sheet 12 --------------------------------------------
MOAT_WIDTH = ft(38, 0)          # bastion face to the counterscarp (37'-6" to 38'-4" measured)
COUNTERSCARP_RADIUS = 14.0      # rounding of the counterscarp around the salients
RAVELIN_GAP = ft(58, 9.75)      # sally port bridge: south curtain to the ravelin gorge
RAVELIN_GORGE_SIDE = ft(36, 7)  # (36'-7" and 35'-1")
RAVELIN_FACE = ft(52, 6)        # (52'-9" and 52'-3")
RAVELIN_MOAT = ft(19, 1)
RAVELIN_TOP = 6.0               # lower than the main walls (sheet 7 elevations, 1936)

# --- Sally port, NPS and sheet 9 ---------------------------------------------------------
SALLY_PORT_WIDTH = ft(9, 0)
SALLY_PORT_HEIGHT = ft(13, 0)

# --- Towers, sheet 5 (1936 main tower details) and sheets 19-21 --------------------------
BELL_TOWER_RADIUS = ft(9, 3.5) / 2          # 1'-10" walls around a 5'-7 1/2" interior
BELL_TOWER_TOP = ft(52, 7)                  # dome top above the moat floor (north elevation)
BELL_TOWER_DOME = ft(5, 11)
BELL_TOWER_OPENINGS = ft(7, 9)              # height of the arched bell openings band
GARITA_RADIUS = ft(5, 10) / 2               # sentry boxes: 5'-10" across
GARITA_BODY = 2.7                           # body height above the parapet top
GARITA_DOME = 0.85
