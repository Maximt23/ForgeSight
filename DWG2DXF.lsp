;;; DWG2DXF.lsp
;;; Super simple: Just converts DWG files to DXF for Python processing
;;; This is all it does - no complex logic that can break!
;;;
;;; Commands:
;;;   DWG2DXF      - Convert current drawing to DXF
;;;   DWG2DXFBATCH - Batch convert all DWGs in Input folder

(vl-load-com)

(setq *DXF_INPUT_FOLDER*  "C:\\Users\\vn59j7j\\OneDrive - Walmart Inc\\Master Excel Pathing\\CADtoSiteOwl\\CadOwl\\Input")
(setq *DXF_OUTPUT_FOLDER* "C:\\Users\\vn59j7j\\OneDrive - Walmart Inc\\Master Excel Pathing\\CADtoSiteOwl\\CadOwl\\DXF")

(defun c:DWG2DXF (/ dwgName dxfPath)
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
