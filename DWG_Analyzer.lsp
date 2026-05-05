;;; DWG_Analyzer.lsp
;;; Diagnostic script to extract layer names, block names, and structure
;;; Run this on a sample DWG, then share the output text file
;;;
;;; Command: ANALYZEDWG

(vl-load-com)

(defun c:ANALYZEDWG (/ doc layers blocks outPath f layerList blockList insertList
                       lay blk ss i ent obj blkName layName pt atts att)
  
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (setq layers (vla-get-Layers doc))
  (setq blocks (vla-get-Blocks doc))
  
  ;; Output file path
  (setq outPath (strcat (getvar "DWGPREFIX") "DWG_Analysis_" 
                        (vl-filename-base (getvar "DWGNAME")) ".txt"))
  
  (setq f (open outPath "w"))
  
  (write-line "========================================" f)
  (write-line "DWG STRUCTURE ANALYSIS" f)
  (write-line (strcat "File: " (getvar "DWGNAME")) f)
  (write-line (strcat "Path: " (getvar "DWGPREFIX")) f)
  (write-line (strcat "Generated: " (menucmd "M=$(edtime,0,YYYY-MO-DD HH:MM)")) f)
  (write-line "========================================" f)
  
  ;; ============================================
  ;; SECTION 1: ALL LAYERS
  ;; ============================================
  (write-line "\n\n=== ALL LAYERS ===" f)
  (write-line "Format: LayerName | On/Off | Frozen | Locked | Color\n" f)
  
  (setq layerList '())
  (vlax-for lay layers
    (setq layerList (cons (vla-get-Name lay) layerList))
    (write-line
      (strcat
        (vla-get-Name lay) " | "
        (if (= (vla-get-LayerOn lay) :vlax-true) "ON" "OFF") " | "
        (if (= (vla-get-Freeze lay) :vlax-true) "FROZEN" "THAWED") " | "
        (if (= (vla-get-Lock lay) :vlax-true) "LOCKED" "UNLOCKED") " | "
        "Color:" (itoa (vla-get-Color lay))
      )
      f
    )
  )
  
  ;; ============================================
  ;; SECTION 2: ALL BLOCK DEFINITIONS
  ;; ============================================
  (write-line "\n\n=== BLOCK DEFINITIONS ===" f)
  (write-line "These are the block templates defined in the drawing.\n" f)
  
  (setq blockList '())
  (vlax-for blk blocks
    (if (and (= (vla-get-IsXref blk) :vlax-false)
             (= (vla-get-IsLayout blk) :vlax-false)
             (not (wcmatch (vla-get-Name blk) "*Model_Space*,*Paper_Space*")))
      (progn
        (setq blockList (cons (vla-get-Name blk) blockList))
        (write-line (vla-get-Name blk) f)
      )
    )
  )
  
  ;; ============================================
  ;; SECTION 3: ALL INSERTED BLOCKS (with layers and positions)
  ;; ============================================
  (write-line "\n\n=== BLOCK INSERTS (First 200) ===" f)
  (write-line "Format: BlockName | Layer | X,Y | Attributes\n" f)
  
  ;; Thaw/unlock all layers first to see everything
  (command "._-LAYER" "_THAW" "*" "_ON" "*" "_UNLOCK" "*" "")
  
  (setq ss (ssget "_X" '((0 . "INSERT"))))
  (setq insertList '())
  
  (if ss
    (progn
      (setq i 0)
      (while (and (< i (sslength ss)) (< i 200))  ; Limit to 200 for sanity
        (setq ent (ssname ss i))
        (setq obj (vlax-ename->vla-object ent))
        
        ;; Get block name (handle dynamic blocks)
        (if (vlax-property-available-p obj 'EffectiveName)
          (setq blkName (vla-get-EffectiveName obj))
          (setq blkName (vla-get-Name obj))
        )
        
        (setq layName (vla-get-Layer obj))
        (setq pt (vlax-get obj 'InsertionPoint))
        
        ;; Get attributes if any
        (setq atts "")
        (if (= (vla-get-HasAttributes obj) :vlax-true)
          (foreach att (vlax-invoke obj 'GetAttributes)
            (setq atts (strcat atts 
                         "[" (vla-get-TagString att) "=" 
                         (vla-get-TextString att) "] "))
          )
        )
        
        ;; Track unique block/layer combos
        (if (not (member (cons blkName layName) insertList))
          (setq insertList (cons (cons blkName layName) insertList))
        )
        
        (write-line
          (strcat
            blkName " | "
            layName " | "
            (rtos (car pt) 2 2) "," (rtos (cadr pt) 2 2) " | "
            atts
          )
          f
        )
        
        (setq i (1+ i))
      )
    )
    (write-line "No INSERT objects found." f)
  )
  
  ;; ============================================
  ;; SECTION 4: UNIQUE BLOCK/LAYER COMBINATIONS
  ;; ============================================
  (write-line "\n\n=== UNIQUE BLOCK + LAYER COMBINATIONS ===" f)
  (write-line "This helps identify device patterns.\n" f)
  
  (foreach combo insertList
    (write-line (strcat "Block: " (car combo) "  |  Layer: " (cdr combo)) f)
  )
  
  ;; ============================================
  ;; SECTION 5: LAYER PATTERNS (for boundary detection)
  ;; ============================================
  (write-line "\n\n=== LAYERS MATCHING COMMON BOUNDARY KEYWORDS ===" f)
  (write-line "Looking for: *BOUND*, *BORDER*, *TITLE*, *AREA*, *PRINT*, *SHEET*\n" f)
  
  (foreach ln layerList
    (if (wcmatch (strcase ln) "*BOUND*,*BORDER*,*TITLE*,*AREA*,*PRINT*,*SHEET*,*TTLB*,*LIMIT*")
      (write-line (strcat "  MATCH: " ln) f)
    )
  )
  
  ;; ============================================
  ;; SECTION 6: LAYERS MATCHING DEVICE KEYWORDS
  ;; ============================================
  (write-line "\n\n=== LAYERS MATCHING DEVICE KEYWORDS ===" f)
  (write-line "Looking for: *CCTV*, *CAM*, *SENSOR*, *SECURITY*, *DEVICE*, *ALARM*\n" f)
  
  (foreach ln layerList
    (if (wcmatch (strcase ln) "*CCTV*,*CAM*,*SENSOR*,*SECURITY*,*DEVICE*,*ALARM*,*VIDEO*,*SURV*,*INTRUSION*")
      (write-line (strcat "  MATCH: " ln) f)
    )
  )
  
  ;; ============================================
  ;; SECTION 7: LARGEST CLOSED POLYLINES (potential boundaries)
  ;; ============================================
  (write-line "\n\n=== LARGEST POLYLINES (Potential Boundaries) ===" f)
  (write-line "Top 10 by area - closed polylines that might be floor boundaries.\n" f)
  
  (setq ss (ssget "_X" '((0 . "LWPOLYLINE"))))
  (if ss
    (progn
      (setq polyList '())
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq obj (vlax-ename->vla-object ent))
        (if (= (vla-get-Closed obj) :vlax-true)
          (progn
            (setq ar (abs (vla-get-Area obj)))
            (setq polyList (cons (list ar (vla-get-Layer obj)) polyList))
          )
        )
        (setq i (1+ i))
      )
      ;; Sort by area descending
      (setq polyList (vl-sort polyList '(lambda (a b) (> (car a) (car b)))))
      ;; Top 10
      (setq i 0)
      (foreach p polyList
        (if (< i 10)
          (progn
            (write-line (strcat "Area: " (rtos (car p) 2 0) " sqft  Layer: " (cadr p)) f)
            (setq i (1+ i))
          )
        )
      )
    )
    (write-line "No LWPOLYLINE objects found." f)
  )
  
  ;; ============================================
  ;; DONE
  ;; ============================================
  (close f)
  
  (prompt (strcat "\n\n✅ Analysis complete! Output saved to:\n" outPath))
  (prompt "\n\nShare this file so we can build your automated script!")
  (princ)
)

(princ "\nLoaded DWG_Analyzer.lsp - Run command: ANALYZEDWG")
(princ)
