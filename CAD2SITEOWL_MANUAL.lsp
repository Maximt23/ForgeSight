;;; CAD_to_SiteOwl_Export.lsp
;;; Purpose:
;;; 1) Thaw/on/unlock all layers
;;; 2) Bind attached XREFs
;;; 3) Let user select the TRUE print/floorplan boundary objects
;;; 4) Let user select CCTV/device block INSERTs
;;; 5) Convert CAD insertion points to SiteOwl coordinates based on:
;;;      1000 x 1000 SiteOwl artboard
;;;      800-wide centered floorplan/object
;;;      SiteOwl origin top-left, bottom-right 100,100
;;; 6) Export CSV with SiteOwl import-style headers
;;;
;;; Command: CAD2SITEOWL
;;;
;;; IMPORTANT:
;;; - This script DOES NOT permanently scale or move your CAD geometry.
;;; - It calculates coordinates as if the selected boundary was placed on a
;;;   1000x1000 artboard with the object scaled to 800 across.
;;; - Use the same boundary selection you use for the final SiteOwl print/PDF.

(vl-load-com)

(setq *SO_ARTBOARD_SIZE* 1000.0)
(setq *SO_OBJECT_WIDTH* 800.0)
(setq *SO_SCALE_MODE* "WIDTH") ; "WIDTH" = object is 800 across. "FIT" = longest side fits inside 800.

(defun SO:CSVSafe (s / t)
  (if (null s) (setq s ""))
  (setq t (vl-princ-to-string s))
  (setq t (vl-string-subst "" "\r" t))
  (setq t (vl-string-subst "" "\n" t))
  (while (vl-string-search "\"" t)
    (setq t (vl-string-subst "\"\"" "\"" t))
  )
  (strcat "\"" t "\"")
)

(defun SO:JoinCSV (lst / out)
  (setq out "")
  (foreach x lst
    (setq out (strcat out (if (= out "") "" ",") (SO:CSVSafe x)))
  )
  out
)

(defun SO:Headers ()
  (list
    "Project ID" "Plan ID" "Primary Device/Task ID" "Primary Device/Task Name"
    "Device ID" "Name" "Abbreviated Names" "Device / Task" "System Type"
    "Device/Task Type" "Part Number" "Manufacturer" "Budgeted Hours" "Budgeted Cost"
    "Assigned To" "Assigned To ID" "Date Due" "Installed/Completed By"
    "Installed/Completed By ID" "Date Installed/Completed" "Priority" "Install Status"
    "Operational Status" "Images" "Serial Number" "IP Address" "MAC Address"
    "Barcode" "IP / Analog" "Interior / Exterior" "Coverage Area" "Coverage Direction"
    "Coverage Angle" "Coverage Range" "Height (ft)" "IDF / MDF" "Hub" "Port"
    "Connection Length (feet)" "Description" "Flagged" "Date Flagged" "Flag Notes"
    "Instructions" "Field Notes" "Labor Warranty Expiration" "Device Warranty Expiration"
    "Replacement Cost" "Custom Device ID" "Project" "Site" "Building" "Plan"
    "Coordinates" "Archived" "Shareable Link"
  )
)

(defun SO:PadToHeaders (row / headers)
  (setq headers (SO:Headers))
  (while (< (length row) (length headers))
    (setq row (append row (list "")))
  )
  row
)

(defun SO:LayerPrep ()
  (prompt "\nThawing, turning on, and unlocking all layers...")
  (command "_.-LAYER" "_THAW" "*" "_ON" "*" "_UNLOCK" "*" "")
)

(defun SO:BindXrefs (/ doc blocks blk name)
  (prompt "\nBinding XREFs if any exist...")
  ;; Try the native command first. If no XREFs exist, AutoCAD may simply report nothing to bind.
  (vl-catch-all-apply
    '(lambda () (command "_.-XREF" "_BIND" "*"))
  )
  ;; Regen after bind attempt.
  (vl-catch-all-apply '(lambda () (command "_.REGEN")))
)

(defun SO:GetEffectiveName (obj / nm)
  (setq nm "")
  (if (vlax-property-available-p obj 'EffectiveName)
    (setq nm (vla-get-EffectiveName obj))
    (setq nm (vla-get-Name obj))
  )
  nm
)

(defun SO:GetAttr (obj tag / val atts a)
  (setq val nil)
  (if (= (vla-get-HasAttributes obj) :vlax-true)
    (progn
      (setq atts (vlax-invoke obj 'GetAttributes))
      (foreach a atts
        (if (= (strcase (vla-get-TagString a)) (strcase tag))
          (setq val (vla-get-TextString a))
        )
      )
    )
  )
  val
)

(defun SO:GetDeviceName (obj / n)
  ;; Change/add tag names here if your CCTV blocks store device names differently.
  (setq n (SO:GetAttr obj "NAME"))
  (if (or (null n) (= n "")) (setq n (SO:GetAttr obj "DEVICE")))
  (if (or (null n) (= n "")) (setq n (SO:GetAttr obj "CAMERA")))
  (if (or (null n) (= n "")) (setq n (SO:GetAttr obj "ID")))
  (if (or (null n) (= n "")) (setq n (SO:GetEffectiveName obj)))
  n
)

(defun SO:UpdateBBoxFromEntity (ent current / obj mn mx pmin pmax minx miny maxx maxy)
  (setq obj (vlax-ename->vla-object ent))
  (if (not (vl-catch-all-error-p
             (vl-catch-all-apply 'vla-GetBoundingBox (list obj 'mn 'mx))))
    (progn
      (setq pmin (vlax-safearray->list mn))
      (setq pmax (vlax-safearray->list mx))
      (if (null current)
        (setq current (list (car pmin) (cadr pmin) (car pmax) (cadr pmax)))
        (progn
          (setq minx (min (nth 0 current) (car pmin)))
          (setq miny (min (nth 1 current) (cadr pmin)))
          (setq maxx (max (nth 2 current) (car pmax)))
          (setq maxy (max (nth 3 current) (cadr pmax)))
          (setq current (list minx miny maxx maxy))
        )
      )
    )
  )
  current
)

(defun SO:GetSelectionBBox (ss / i bbox)
  (setq i 0 bbox nil)
  (while (< i (sslength ss))
    (setq bbox (SO:UpdateBBoxFromEntity (ssname ss i) bbox))
    (setq i (1+ i))
  )
  bbox
)

(defun SO:PtToSiteOwl (pt bbox / minx miny maxx maxy w h scale scaledW scaledH offX offY artX artY siteX siteY)
  (setq minx (nth 0 bbox))
  (setq miny (nth 1 bbox))
  (setq maxx (nth 2 bbox))
  (setq maxy (nth 3 bbox))
  (setq w (- maxx minx))
  (setq h (- maxy miny))
  (if (or (<= w 0.0) (<= h 0.0))
    nil
    (progn
      (if (= (strcase *SO_SCALE_MODE*) "FIT")
        (setq scale (/ *SO_OBJECT_WIDTH* (max w h)))
        (setq scale (/ *SO_OBJECT_WIDTH* w))
      )
      (setq scaledW (* w scale))
      (setq scaledH (* h scale))
      (setq offX (/ (- *SO_ARTBOARD_SIZE* scaledW) 2.0))
      (setq offY (/ (- *SO_ARTBOARD_SIZE* scaledH) 2.0))
      ;; CAD X right = artboard X right.
      (setq artX (+ offX (* (- (car pt) minx) scale)))
      ;; CAD Y up, SiteOwl/artboard Y down. Flip using maxY - CAD_Y.
      (setq artY (+ offY (* (- maxy (cadr pt)) scale)))
      (setq siteX (/ artX 10.0))
      (setq siteY (/ artY 10.0))
      (list siteX siteY artX artY)
    )
  )
)

(defun SO:MakeRow (obj coord / name blockName layer x y coordText row)
  (setq name (SO:GetDeviceName obj))
  (setq blockName (SO:GetEffectiveName obj))
  (setq layer (vla-get-Layer obj))
  (setq x (rtos (car coord) 2 2))
  (setq y (rtos (cadr coord) 2 2))
  (setq coordText (strcat "(" x ", " y ")"))

  ;; This row aligns exactly to the uploaded 56-column SiteOwl-style template.
  ;; Adjust fixed defaults here if needed.
  (SO:PadToHeaders
    (list
      ""                         ; Project ID
      ""                         ; Plan ID
      ""                         ; Primary Device/Task ID
      name                       ; Primary Device/Task Name
      ""                         ; Device ID
      name                       ; Name
      blockName                  ; Abbreviated Names
      "Device"                   ; Device / Task
      "Video Surveillance"       ; System Type
      "Fixed Camera"             ; Device/Task Type
      ""                         ; Part Number
      ""                         ; Manufacturer
      ""                         ; Budgeted Hours
      ""                         ; Budgeted Cost
      ""                         ; Assigned To
      ""                         ; Assigned To ID
      ""                         ; Date Due
      ""                         ; Installed/Completed By
      ""                         ; Installed/Completed By ID
      ""                         ; Date Installed/Completed
      ""                         ; Priority
      ""                         ; Install Status
      ""                         ; Operational Status
      ""                         ; Images
      ""                         ; Serial Number
      ""                         ; IP Address
      ""                         ; MAC Address
      ""                         ; Barcode
      ""                         ; IP / Analog
      "Interior"                 ; Interior / Exterior
      ""                         ; Coverage Area
      ""                         ; Coverage Direction
      ""                         ; Coverage Angle
      ""                         ; Coverage Range
      ""                         ; Height (ft)
      ""                         ; IDF / MDF
      ""                         ; Hub
      ""                         ; Port
      ""                         ; Connection Length (feet)
      (strcat "Imported from CAD layer: " layer) ; Description
      ""                         ; Flagged
      ""                         ; Date Flagged
      ""                         ; Flag Notes
      ""                         ; Instructions
      ""                         ; Field Notes
      ""                         ; Labor Warranty Expiration
      ""                         ; Device Warranty Expiration
      ""                         ; Replacement Cost
      ""                         ; Custom Device ID
      ""                         ; Project
      ""                         ; Site
      ""                         ; Building
      ""                         ; Plan
      coordText                  ; Coordinates
      ""                         ; Archived
      ""                         ; Shareable Link
    )
  )
)

(defun c:CAD2SITEOWL (/ oldcmdecho boundarySS deviceSS bbox filePath f i ent obj ipt pt conv row count minx miny maxx maxy)
  (setq oldcmdecho (getvar "CMDECHO"))
  (setvar "CMDECHO" 0)

  (defun *error* (msg)
    (if f (close f))
    (if oldcmdecho (setvar "CMDECHO" oldcmdecho))
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*")))
      (prompt (strcat "\nERROR: " msg))
    )
    (princ)
  )

  (SO:LayerPrep)
  (SO:BindXrefs)

  (prompt "\nSelect the TRUE floorplan/print boundary objects used for the SiteOwl print: ")
  (setq boundarySS (ssget))
  (if (null boundarySS)
    (progn (prompt "\nNothing selected. Command cancelled.") (*error* "CANCEL"))
  )

  (setq bbox (SO:GetSelectionBBox boundarySS))
  (if (null bbox)
    (progn (prompt "\nCould not calculate boundary extents. Command cancelled.") (*error* "CANCEL"))
  )

  (setq minx (nth 0 bbox) miny (nth 1 bbox) maxx (nth 2 bbox) maxy (nth 3 bbox))
  (prompt
    (strcat
      "\nBoundary extents used: "
      "MinX=" (rtos minx 2 4) ", MinY=" (rtos miny 2 4)
      ", MaxX=" (rtos maxx 2 4) ", MaxY=" (rtos maxy 2 4)
    )
  )

  (prompt "\nSelect CCTV/device block INSERTS to export: ")
  (setq deviceSS (ssget '((0 . "INSERT"))))
  (if (null deviceSS)
    (progn (prompt "\nNo block inserts selected. Command cancelled.") (*error* "CANCEL"))
  )

  (setq filePath (getfiled "Save SiteOwl coordinate CSV" (strcat (getvar "DWGPREFIX") "SiteOwl_CAD_Export.csv") "csv" 1))
  (if (null filePath)
    (progn (prompt "\nNo output file selected. Command cancelled.") (*error* "CANCEL"))
  )

  (setq f (open filePath "w"))
  (write-line (SO:JoinCSV (SO:Headers)) f)

  (setq i 0 count 0)
  (while (< i (sslength deviceSS))
    (setq ent (ssname deviceSS i))
    (setq obj (vlax-ename->vla-object ent))
    (setq ipt (vlax-get obj 'InsertionPoint))
    (setq pt (list (car ipt) (cadr ipt)))
    (setq conv (SO:PtToSiteOwl pt bbox))
    (if conv
      (progn
        (setq row (SO:MakeRow obj conv))
        (write-line (SO:JoinCSV row) f)
        (setq count (1+ count))
      )
    )
    (setq i (1+ i))
  )

  (close f)
  (setq f nil)
  (setvar "CMDECHO" oldcmdecho)

  (prompt (strcat "\nDone. Exported " (itoa count) " devices to: " filePath))
  (prompt "\nCoordinates are based on a 1000x1000 artboard with the selected boundary scaled to 800 across.")
  (princ)
)

(princ "\nLoaded CAD_to_SiteOwl_Export.lsp. Run command: CAD2SITEOWL")
(princ)
