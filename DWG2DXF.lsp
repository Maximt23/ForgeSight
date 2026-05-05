;;; DWG2DXF.lsp
;;; Super simple: Just converts DWG files to DXF for Python processing
;;; This is all it does - no complex logic that can break!
;;;
;;; Commands:
;;;   DWG2DXF      - Convert current drawing to DXF
;;;   DWG2DXFBATCH - Batch convert all DWGs in Input folder

(vl-load-com)

;;; ============================================================
;;; CONFIGURATION - Auto-detects paths from script location
;;; ============================================================
;;; After loading, the script finds Input/ and Output/ folders
;;; relative to where this .lsp file is located.
;;;
;;; Structure expected:
;;;   YourFolder/
;;;   ├── DWG2DXF.lsp    (this file)
;;;   ├── Input/         (put DWG files here, DXF saved here)
;;;   └── Output/        (CSV files from Python script)
;;; ============================================================

(vl-load-com)

;; Auto-detect script location and set paths
(defun DXF:SetPaths (/ scriptPath)
  (setq scriptPath (findfile "DWG2DXF.lsp"))
  (if scriptPath
    (progn
      (setq *DXF_BASE_FOLDER* (vl-filename-directory scriptPath))
      (setq *DXF_INPUT_FOLDER* (strcat *DXF_BASE_FOLDER* "\\Input"))
      (setq *DXF_OUTPUT_FOLDER* (strcat *DXF_BASE_FOLDER* "\\Input"))  ;; DXF goes to Input folder
      (princ (strcat "\nPaths configured:"))
      (princ (strcat "\n  Input:  " *DXF_INPUT_FOLDER*))
      (princ (strcat "\n  Output: " *DXF_OUTPUT_FOLDER*))
    )
    (progn
      ;; Fallback to current drawing folder
      (setq *DXF_BASE_FOLDER* (getvar "DWGPREFIX"))
      (setq *DXF_INPUT_FOLDER* (strcat *DXF_BASE_FOLDER* "Input"))
      (setq *DXF_OUTPUT_FOLDER* (strcat *DXF_BASE_FOLDER* "Input"))
      (princ "\nWARNING: Could not find script location, using drawing folder.")
    )
  )
)

;; Initialize paths on load
(DXF:SetPaths)
  "Convert current drawing to DXF"
  (setq dwgName (vl-filename-base (getvar "DWGNAME")))
  
  ;; Ensure output folder exists
  (if (not (vl-file-directory-p *DXF_OUTPUT_FOLDER*))
    (vl-mkdir *DXF_OUTPUT_FOLDER*)
  )
  
  (setq dxfPath (strcat *DXF_OUTPUT_FOLDER* "\\" dwgName ".dxf"))
  
  ;; Thaw/unlock all layers first
  (command-s "._-LAYER" "_THAW" "*" "_ON" "*" "_UNLOCK" "*" "")
  
  ;; Bind XREFs
  (vl-catch-all-apply '(lambda () (command-s "._-XREF" "_B" "*" "")))
  
  ;; Save as DXF (AutoCAD 2018 DXF format)
  (command-s "._SAVEAS" "DXF" "V" "2018" dxfPath)
  
  (princ (strcat "\n✅ Exported: " dxfPath))
  (princ)
)

(defun c:DWG2DXFBATCH (/ files f dwgPath dwgName dxfPath)
  "Batch convert all DWGs in Input folder to DXF"
  
  (princ "\n============================================")
  (princ "\n  DWG → DXF BATCH CONVERTER")
  (princ (strcat "\n  Input:  " *DXF_INPUT_FOLDER*))
  (princ (strcat "\n  Output: " *DXF_OUTPUT_FOLDER*))
  (princ "\n============================================\n")
  
  ;; Verify input folder exists
  (if (not (vl-file-directory-p *DXF_INPUT_FOLDER*))
    (progn
      (princ (strcat "\n*** ERROR: Input folder does not exist: " *DXF_INPUT_FOLDER*))
      (exit)
    )
  )
  
  ;; Create output folder
  (if (not (vl-file-directory-p *DXF_OUTPUT_FOLDER*))
    (vl-mkdir *DXF_OUTPUT_FOLDER*)
  )
  
  ;; Get all DWG files
  (setq files (vl-directory-files *DXF_INPUT_FOLDER* "*.dwg" 1))
  
  (if (null files)
    (progn
      (princ "\n*** No DWG files found in Input folder! ***")
      (exit)
    )
  )
  
  (princ (strcat "\nFound " (itoa (length files)) " DWG files...\n"))
  
  (foreach f files
    (setq dwgPath (strcat *DXF_INPUT_FOLDER* "\\" f))
    (setq dwgName (vl-filename-base f))
    (setq dxfPath (strcat *DXF_OUTPUT_FOLDER* "\\" dwgName ".dxf"))
    
    (princ (strcat "\nProcessing: " f))
    
    (vl-catch-all-apply
      '(lambda ()
        ;; Open file
        (command-s "._OPEN" dwgPath "_Y")
        
        ;; Thaw/unlock all layers
        (command-s "._-LAYER" "_THAW" "*" "_ON" "*" "_UNLOCK" "*" "")
        
        ;; Bind XREFs
        (vl-catch-all-apply '(lambda () (command-s "._-XREF" "_B" "*" "")))
        
        ;; Save as DXF
        (command-s "._SAVEAS" "DXF" "V" "2018" dxfPath)
        
        ;; Close without saving DWG
        (command-s "._CLOSE" "_N")
        
        (princ " ✅")
      )
    )
  )
  
  (princ "\n\n============================================")
  (princ "\n  BATCH COMPLETE")
  (princ (strcat "\n  DXF files saved to: " *DXF_OUTPUT_FOLDER*))
  (princ "\n  Now run: python cad2siteowl.py")
  (princ "\n============================================\n")
  (princ)
)

(princ "\n============================================")
(princ "\n  DWG2DXF Converter Loaded")
(princ "\n  Commands: DWG2DXF | DWG2DXFBATCH")
(princ "\n============================================")
(princ)
