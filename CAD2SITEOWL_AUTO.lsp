;;; ============================================================
;;; CAD2SITEOWL_AUTO.lsp
;;; BULLETPROOF AUTOMATED CAD → SITEOWL COORDINATE EXPORTER
;;; ============================================================
;;; 
;;; Features:
;;;   - Zero user interaction (fully automated)
;;;   - Configurable boundary detection (layer, block, or largest polyline)
;;;   - Configurable device detection (layer patterns, block patterns)
;;;   - Batch mode for processing entire folders
;;;   - Comprehensive logging
;;;   - Non-destructive (never modifies source files)
;;;
;;; Commands:
;;;   CAD2SO        - Process current drawing
;;;   CAD2SOBATCH   - Batch process Input folder
;;;
;;; ============================================================

(vl-load-com)

;;; ============================================================
;;; CONFIGURATION - EDIT THESE TO MATCH YOUR STANDARDS
;;; ============================================================

;; INPUT/OUTPUT FOLDERS (for batch mode)
(setq *SO_INPUT_FOLDER*  "C:\\Users\\vn59j7j\\OneDrive - Walmart Inc\\Master Excel Pathing\\CADtoSiteOwl\\Input")
(setq *SO_OUTPUT_FOLDER* "C:\\Users\\vn59j7j\\OneDrive - Walmart Inc\\Master Excel Pathing\\CADtoSiteOwl\\Output")

;; SITEOWL COORDINATE SETTINGS
(setq *SO_ARTBOARD_SIZE* 1000.0)
(setq *SO_OBJECT_WIDTH*  800.0)
(setq *SO_SCALE_MODE*    "WIDTH")  ; "WIDTH" or "FIT"

;; BOUNDARY DETECTION SETTINGS
;; Method: "LAYER", "BLOCK", "LARGEST_POLY", or "DRAWING_EXTENTS"
(setq *SO_BOUNDARY_METHOD* "LARGEST_POLY")

;; If using LAYER method - comma-separated wildcard patterns
(setq *SO_BOUNDARY_LAYERS* "A-ANNO-TTLB*,*BOUNDARY*,*BORDER*,*PRINT*,*LIMIT*")

;; If using BLOCK method - comma-separated wildcard patterns  
(setq *SO_BOUNDARY_BLOCKS* "TITLEBLOCK*,BORDER*,*SHEET*")

;; DEVICE DETECTION SETTINGS
;; Layer patterns for device blocks (wildcards OK)
(setq *SO_DEVICE_LAYERS* "S-CCTV*,*CCTV*,*CAMERA*,*SECURITY*,*VIDEO*,*SURV*,*DEVICE*")

;; Block name patterns for devices (wildcards OK)
(setq *SO_DEVICE_BLOCKS* "CAM*,CAMERA*,DOME*,PTZ*,BULLET*,CCTV*,*DEVICE*")

;; Attribute tags to try for device names (in order of preference)
(setq *SO_NAME_TAGS* '("NAME" "DEVICE" "CAMERA" "ID" "TAG" "NUMBER" "CAM_ID" "DEVICE_ID"))

;; LOGGING
(setq *SO_LOG_ENABLED* T)
(setq *SO_LOG_FILE* nil)  ; Set dynamically per file

;;; ============================================================
;;; LOGGING FUNCTIONS
;;; ============================================================

(defun SO:Log (msg / timestamp)
  (if *SO_LOG_ENABLED*
    (progn
      (setq timestamp (menucmd "M=$(edtime,0,HH:MM:SS)"))
      (if *SO_LOG_FILE*
        (progn
          (setq logF (open *SO_LOG_FILE* "a"))
          (write-line (strcat "[" timestamp "] " msg) logF)
          (close logF)
        )
      )
      (princ (strcat "\n[LOG] " msg))
    )
  )
)

(defun SO:InitLog (dwgName / logPath)
  (setq logPath (strcat *SO_OUTPUT_FOLDER* "\\" 
                        (vl-filename-base dwgName) "_log.txt"))
  (setq *SO_LOG_FILE* logPath)
  (setq logF (open logPath "w"))
  (write-line "============================================" logF)
  (write-line "CAD2SITEOWL PROCESSING LOG" logF)
  (write-line (strcat "Source: " dwgName) logF)
  (write-line (strcat "Started: " (menucmd "M=$(edtime,0,YYYY-MO-DD HH:MM:SS)")) logF)
  (write-line "============================================" logF)
  (close logF)
)

;;; ============================================================
;;; CSV UTILITIES
;;; ============================================================

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

;;; ============================================================
;;; LAYER PREPARATION
;;; ============================================================

(defun SO:LayerPrep ()
  (SO:Log "Thawing, turning on, and unlocking all layers...")
  (vl-catch-all-apply
    '(lambda ()
      (command-s "._-LAYER" "_THAW" "*" "_ON" "*" "_UNLOCK" "*" "")
    )
  )
  (SO:Log "Layer prep complete.")
)

;;; ============================================================
;;; XREF BINDING
;;; ============================================================

(defun SO:BindXrefs (/ xrefCount)
  (SO:Log "Attempting to bind XREFs...")
  (vl-catch-all-apply
    '(lambda ()
      (command-s "._-XREF" "_B" "*" "")
    )
  )
  (vl-catch-all-apply '(lambda () (command-s "._REGEN")))
  (SO:Log "XREF binding attempted.")
)

;;; ============================================================
;;; HELPER FUNCTIONS
;;; ============================================================

(defun SO:MatchesPattern (str patterns / patList match)
  "Check if STR matches any of the comma-separated wildcard PATTERNS"
  (setq patList (SO:SplitString patterns ","))
  (setq match nil)
  (foreach pat patList
    (setq pat (vl-string-trim " " pat))
    (if (wcmatch (strcase str) (strcase pat))
      (setq match T)
    )
  )
  match
)

(defun SO:SplitString (str delim / pos result part)
  "Split string by delimiter"
  (setq result '())
  (while (setq pos (vl-string-search delim str))
    (setq part (substr str 1 pos))
    (setq result (cons part result))
    (setq str (substr str (+ pos 2)))
  )
  (setq result (cons str result))
  (reverse result)
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
  "Try multiple attribute tags to find device name"
  (setq n nil)
  (foreach tag *SO_NAME_TAGS*
    (if (or (null n) (= n ""))
      (setq n (SO:GetAttr obj tag))
    )
  )
  (if (or (null n) (= n ""))
    (setq n (SO:GetEffectiveName obj))
  )
  n
)

;;; ============================================================
;;; BOUNDING BOX UTILITIES
;;; ============================================================

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

;;; ============================================================
;;; BOUNDARY DETECTION (AUTO)
;;; ============================================================

(defun SO:FindBoundary_ByLayer (/ ss)
  "Find boundary by layer pattern"
  (SO:Log (strcat "Looking for boundary on layers: " *SO_BOUNDARY_LAYERS*))
  (setq ss nil)
  (foreach layPat (SO:SplitString *SO_BOUNDARY_LAYERS* ",")
    (setq layPat (vl-string-trim " " layPat))
    (if (null ss)
      (setq ss (ssget "_X" (list (cons 8 layPat))))
      ;; Merge selection sets
      (progn
        (setq ss2 (ssget "_X" (list (cons 8 layPat))))
        (if ss2
          (progn
            (setq i 0)
            (while (< i (sslength ss2))
              (ssadd (ssname ss2 i) ss)
              (setq i (1+ i))
            )
          )
        )
      )
    )
  )
  (if ss
    (SO:Log (strcat "Found " (itoa (sslength ss)) " boundary objects by layer"))
    (SO:Log "WARNING: No boundary objects found by layer pattern!")
  )
  ss
)

(defun SO:FindBoundary_ByBlock (/ ss)
  "Find boundary by block name pattern"
  (SO:Log (strcat "Looking for boundary blocks: " *SO_BOUNDARY_BLOCKS*))
  (setq ss (ssget "_X" '((0 . "INSERT"))))
  (if ss
    (progn
      (setq filtered (ssadd))
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq obj (vlax-ename->vla-object ent))
        (setq blkName (SO:GetEffectiveName obj))
        (if (SO:MatchesPattern blkName *SO_BOUNDARY_BLOCKS*)
          (ssadd ent filtered)
        )
        (setq i (1+ i))
      )
      (if (> (sslength filtered) 0)
        (progn
          (SO:Log (strcat "Found " (itoa (sslength filtered)) " boundary blocks"))
          (setq ss filtered)
        )
        (progn
          (SO:Log "WARNING: No boundary blocks found!")
          (setq ss nil)
        )
      )
    )
  )
  ss
)

(defun SO:FindBoundary_LargestPoly (/ ss largest largestArea i ent obj ar)
  "Find the largest closed polyline as boundary"
  (SO:Log "Looking for largest closed polyline as boundary...")
  (setq ss (ssget "_X" '((0 . "LWPOLYLINE"))))
  (setq largest nil largestArea 0)
  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq obj (vlax-ename->vla-object ent))
        (if (= (vla-get-Closed obj) :vlax-true)
          (progn
            (setq ar (abs (vla-get-Area obj)))
            (if (> ar largestArea)
              (progn
                (setq largestArea ar)
                (setq largest ent)
              )
            )
          )
        )
        (setq i (1+ i))
      )
    )
  )
  (if largest
    (progn
      (SO:Log (strcat "Found largest polyline with area: " (rtos largestArea 2 0)))
      (setq ss (ssadd))
      (ssadd largest ss)
      ss
    )
    (progn
      (SO:Log "WARNING: No closed polylines found!")
      nil
    )
  )
)

(defun SO:FindBoundary_Extents (/ doc mspace mn mx pmin pmax)
  "Use drawing model space extents as boundary"
  (SO:Log "Using drawing extents as boundary...")
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (setq mspace (vla-get-ModelSpace doc))
  
  ;; Force regen to update extents
  (vl-catch-all-apply '(lambda () (command-s "._ZOOM" "_E")))
  
  ;; Get extents from system variables
  (setq pmin (getvar "EXTMIN"))
  (setq pmax (getvar "EXTMAX"))
  
  (if (and pmin pmax
           (not (equal pmin '(1.0e+20 1.0e+20 1.0e+20)))
           (not (equal pmax '(-1.0e+20 -1.0e+20 -1.0e+20))))
    (progn
      (SO:Log (strcat "Drawing extents: " 
                      (rtos (car pmin) 2 2) "," (rtos (cadr pmin) 2 2) " to "
                      (rtos (car pmax) 2 2) "," (rtos (cadr pmax) 2 2)))
      (list (car pmin) (cadr pmin) (car pmax) (cadr pmax))
    )
    (progn
      (SO:Log "ERROR: Could not determine drawing extents!")
      nil
    )
  )
)

(defun SO:AutoDetectBoundary (/ ss bbox)
  "Auto-detect boundary based on configured method"
  (SO:Log (strcat "Boundary detection method: " *SO_BOUNDARY_METHOD*))
  
  (cond
    ((= (strcase *SO_BOUNDARY_METHOD*) "LAYER")
     (setq ss (SO:FindBoundary_ByLayer))
     (if ss (setq bbox (SO:GetSelectionBBox ss)))
    )
    
    ((= (strcase *SO_BOUNDARY_METHOD*) "BLOCK")
     (setq ss (SO:FindBoundary_ByBlock))
     (if ss (setq bbox (SO:GetSelectionBBox ss)))
    )
    
    ((= (strcase *SO_BOUNDARY_METHOD*) "LARGEST_POLY")
     (setq ss (SO:FindBoundary_LargestPoly))
     (if ss (setq bbox (SO:GetSelectionBBox ss)))
    )
    
    ((= (strcase *SO_BOUNDARY_METHOD*) "DRAWING_EXTENTS")
     (setq bbox (SO:FindBoundary_Extents))
    )
    
    (T
     (SO:Log "Unknown boundary method, falling back to LARGEST_POLY")
     (setq ss (SO:FindBoundary_LargestPoly))
     (if ss (setq bbox (SO:GetSelectionBBox ss)))
    )
  )
  
  ;; Fallback chain if primary method fails
  (if (null bbox)
    (progn
      (SO:Log "Primary boundary detection failed, trying fallbacks...")
      (if (null bbox) (progn
        (setq ss (SO:FindBoundary_LargestPoly))
        (if ss (setq bbox (SO:GetSelectionBBox ss)))
      ))
      (if (null bbox) (setq bbox (SO:FindBoundary_Extents)))
    )
  )
  
  (if bbox
    (SO:Log (strcat "Final boundary: "
                    (rtos (nth 0 bbox) 2 2) "," (rtos (nth 1 bbox) 2 2) " to "
                    (rtos (nth 2 bbox) 2 2) "," (rtos (nth 3 bbox) 2 2)))
    (SO:Log "CRITICAL: Could not determine boundary!")
  )
  
  bbox
)

;;; ============================================================
;;; DEVICE DETECTION (AUTO)
;;; ============================================================

(defun SO:AutoDetectDevices (/ ss filtered i ent obj blkName layName matchLayer matchBlock)
  "Auto-detect device blocks based on layer and block patterns"
  (SO:Log "Auto-detecting device blocks...")
  (SO:Log (strcat "  Layer patterns: " *SO_DEVICE_LAYERS*))
  (SO:Log (strcat "  Block patterns: " *SO_DEVICE_BLOCKS*))
  
  (setq ss (ssget "_X" '((0 . "INSERT"))))
  
  (if (null ss)
    (progn
      (SO:Log "No INSERT objects found in drawing!")
      nil
    )
    (progn
      (setq filtered (ssadd))
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq obj (vlax-ename->vla-object ent))
        (setq blkName (SO:GetEffectiveName obj))
        (setq layName (vla-get-Layer obj))
        
        ;; Check if layer OR block name matches patterns
        (setq matchLayer (SO:MatchesPattern layName *SO_DEVICE_LAYERS*))
        (setq matchBlock (SO:MatchesPattern blkName *SO_DEVICE_BLOCKS*))
        
        (if (or matchLayer matchBlock)
          (ssadd ent filtered)
        )
        
        (setq i (1+ i))
      )
      
      (if (> (sslength filtered) 0)
        (SO:Log (strcat "Found " (itoa (sslength filtered)) " device blocks"))
        (SO:Log "WARNING: No matching device blocks found!")
      )
      
      (if (> (sslength filtered) 0) filtered nil)
    )
  )
)

;;; ============================================================
;;; COORDINATE CONVERSION
;;; ============================================================

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
      (setq artX (+ offX (* (- (car pt) minx) scale)))
      (setq artY (+ offY (* (- maxy (cadr pt)) scale)))
      (setq siteX (/ artX 10.0))
      (setq siteY (/ artY 10.0))
      (list siteX siteY artX artY)
    )
  )
)

;;; ============================================================
;;; ROW BUILDER
;;; ============================================================

(defun SO:MakeRow (obj coord storeNum / name blockName layer x y coordText row)
  (setq name (SO:GetDeviceName obj))
  (setq blockName (SO:GetEffectiveName obj))
  (setq layer (vla-get-Layer obj))
  (setq x (rtos (car coord) 2 2))
  (setq y (rtos (cadr coord) 2 2))
  (setq coordText (strcat "(" x ", " y ")"))

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
      (strcat "Store " storeNum " | Layer: " layer " | Block: " blockName) ; Description
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
      storeNum                   ; Site (store number)
      ""                         ; Building
      ""                         ; Plan
      coordText                  ; Coordinates
      ""                         ; Archived
      ""                         ; Shareable Link
    )
  )
)

;;; ============================================================
;;; STORE NUMBER EXTRACTION
;;; ============================================================

(defun SO:ExtractStoreNumber (name / i start count result)
  "Extract 3-4 digit store number from filename"
  (setq i 1 result nil)
  (while (and (<= i (strlen name)) (not result))
    (if (wcmatch (substr name i 1) "#")
      (progn
        (setq start i count 0)
        (while (and (<= i (strlen name))
                    (wcmatch (substr name i 1) "#"))
          (setq count (1+ count))
          (setq i (1+ i))
        )
        (if (and (>= count 3) (<= count 4))
          (setq result (substr name start count))
        )
      )
      (setq i (1+ i))
    )
  )
  (if (null result) "UNKNOWN" result)
)

;;; ============================================================
;;; MAIN PROCESSING FUNCTION
;;; ============================================================

(defun SO:ProcessCurrentDrawing (/ dwgName storeNum bbox deviceSS csvPath f i ent obj ipt pt conv row count)
  "Process the currently open drawing - fully automated"
  
  (setq dwgName (getvar "DWGNAME"))
  (setq storeNum (SO:ExtractStoreNumber dwgName))
  
  (SO:InitLog dwgName)
  (SO:Log (strcat "Processing: " dwgName))
  (SO:Log (strcat "Store Number: " storeNum))
  
  ;; Step 1: Layer prep
  (SO:LayerPrep)
  
  ;; Step 2: Bind XREFs
  (SO:BindXrefs)
  
  ;; Step 3: Auto-detect boundary
  (setq bbox (SO:AutoDetectBoundary))
  (if (null bbox)
    (progn
      (SO:Log "FATAL: Could not detect boundary. Aborting.")
      (princ "\n*** FAILED: Could not detect boundary! ***")
      nil
    )
    (progn
      ;; Step 4: Auto-detect devices
      (setq deviceSS (SO:AutoDetectDevices))
      
      (if (null deviceSS)
        (progn
          (SO:Log "WARNING: No devices found. Creating empty CSV.")
          (setq count 0)
        )
        (setq count (sslength deviceSS))
      )
      
      ;; Step 5: Create output CSV
      (setq csvPath (strcat *SO_OUTPUT_FOLDER* "\\" 
                            storeNum "_SiteOwl_Export.csv"))
      
      ;; Ensure output folder exists
      (if (not (vl-file-directory-p *SO_OUTPUT_FOLDER*))
        (vl-mkdir *SO_OUTPUT_FOLDER*)
      )
      
      (setq f (open csvPath "w"))
      (write-line (SO:JoinCSV (SO:Headers)) f)
      
      ;; Step 6: Process devices
      (if deviceSS
        (progn
          (setq i 0)
          (while (< i (sslength deviceSS))
            (setq ent (ssname deviceSS i))
            (setq obj (vlax-ename->vla-object ent))
            (setq ipt (vlax-get obj 'InsertionPoint))
            (setq pt (list (car ipt) (cadr ipt)))
            (setq conv (SO:PtToSiteOwl pt bbox))
            (if conv
              (progn
                (setq row (SO:MakeRow obj conv storeNum))
                (write-line (SO:JoinCSV row) f)
              )
            )
            (setq i (1+ i))
          )
        )
      )
      
      (close f)
      
      (SO:Log (strcat "SUCCESS: Exported " (itoa count) " devices"))
      (SO:Log (strcat "Output: " csvPath))
      
      (princ (strcat "\n✅ Exported " (itoa count) " devices to: " csvPath))
      count
    )
  )
)

;;; ============================================================
;;; SINGLE FILE COMMAND
;;; ============================================================

(defun c:CAD2SO (/ oldcmdecho)
  "Process current drawing - fully automated"
  (setq oldcmdecho (getvar "CMDECHO"))
  (setvar "CMDECHO" 0)
  
  (defun *error* (msg)
    (if oldcmdecho (setvar "CMDECHO" oldcmdecho))
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*")))
      (progn
        (SO:Log (strcat "ERROR: " msg))
        (princ (strcat "\n*** ERROR: " msg " ***"))
      )
    )
    (princ)
  )
  
  (SO:ProcessCurrentDrawing)
  
  (setvar "CMDECHO" oldcmdecho)
  (princ)
)

;;; ============================================================
;;; BATCH PROCESSING COMMAND
;;; ============================================================

(defun c:CAD2SOBATCH (/ files f dwgPath processed failed total)
  "Batch process all DWGs in Input folder"
  
  (princ "\n============================================")
  (princ "\n  CAD2SITEOWL BATCH PROCESSOR")
  (princ (strcat "\n  Input:  " *SO_INPUT_FOLDER*))
  (princ (strcat "\n  Output: " *SO_OUTPUT_FOLDER*))
  (princ "\n============================================\n")
  
  ;; Verify folders exist
  (if (not (vl-file-directory-p *SO_INPUT_FOLDER*))
    (progn
      (princ (strcat "\n*** ERROR: Input folder does not exist: " *SO_INPUT_FOLDER*))
      (exit)
    )
  )
  
  (if (not (vl-file-directory-p *SO_OUTPUT_FOLDER*))
    (vl-mkdir *SO_OUTPUT_FOLDER*)
  )
  
  ;; Get all DWG files
  (setq files (vl-directory-files *SO_INPUT_FOLDER* "*.dwg" 1))
  
  (if (null files)
    (progn
      (princ "\n*** No DWG files found in Input folder! ***")
      (exit)
    )
  )
  
  (setq total (length files))
  (setq processed 0 failed 0)
  
  (princ (strcat "\nFound " (itoa total) " DWG files to process...\n"))
  
  (foreach f files
    (setq dwgPath (strcat *SO_INPUT_FOLDER* "\\" f))
    (princ (strcat "\n[" (itoa (+ processed failed 1)) "/" (itoa total) "] " f))
    
    (vl-catch-all-apply
      '(lambda ()
        ;; Open file read-only
        (command-s "._OPEN" dwgPath "_Y")
        
        ;; Process it
        (if (SO:ProcessCurrentDrawing)
          (setq processed (1+ processed))
          (setq failed (1+ failed))
        )
        
        ;; Close without saving (non-destructive!)
        (command-s "._CLOSE" "_N")
      )
    )
  )
  
  (princ "\n\n============================================")
  (princ "\n  BATCH COMPLETE")
  (princ (strcat "\n  Processed: " (itoa processed) "/" (itoa total)))
  (if (> failed 0)
    (princ (strcat "\n  Failed:    " (itoa failed)))
  )
  (princ (strcat "\n  Output:    " *SO_OUTPUT_FOLDER*))
  (princ "\n============================================\n")
  
  (princ)
)

;;; ============================================================
;;; LOAD MESSAGE
;;; ============================================================

(princ "\n============================================")
(princ "\n  CAD2SITEOWL AUTO v2.0 LOADED")
(princ "\n  Commands:")
(princ "\n    CAD2SO      - Process current drawing")
(princ "\n    CAD2SOBATCH - Batch process Input folder")
(princ "\n============================================")
(princ)
