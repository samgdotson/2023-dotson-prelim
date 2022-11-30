@echo off

SET manuscript=thesis
SET references=$(wildcard *.bib)
SET latexopt=-shell-escape -halt-on-error -file-line-error 

IF /I "%1"=="all" GOTO all
IF /I "%1"=="all-via-pdf" GOTO all-via-pdf
IF /I "%1"=="all-via-dvi" GOTO all-via-dvi
IF /I "%1"=="epub" GOTO epub
IF /I "%1"=="clean" GOTO clean
IF /I "%1"=="realclean" GOTO realclean
IF /I "%1"=="%.ps " GOTO %.ps 
IF /I "%1"=="%.png " GOTO %.png 
IF /I "%1"=="zip" GOTO zip
IF /I "%1"=="" GOTO all
GOTO error

:all
	CALL make.bat all-via-pdf
	GOTO :EOF

:all-via-pdf
	CALL make.bat $(manuscript).tex
	CALL make.bat $(references)
	pdflatex -shell-escape %manuscript%.tex
	biber %manuscript%
	pdflatex %latexopt% $<
	pdflatex %latexopt% $<
	GOTO :EOF

:all-via-dvi
	latex %latexopt% %manuscript%
	biber %manuscript%
	latex %latexopt% %manuscript%
	latex %latexopt% %manuscript%
	dvipdf %manuscript%
	GOTO :EOF

:epub
	latex %latexopt% %manuscript%
	biber %manuscript%
	mk4ht htlatex %manuscript%.tex 'xhtml,charset=utf-8,pmathml' ' -cunihtf -utf8 -cvalidate'
	ebook-convert %manuscript%.html %manuscript%.epub
	GOTO :EOF

:clean
	DEL /Q *.dvi *.toc *.aux *.gz *.out *.log *.bbl *.blg *.log *.spl *~ *.spl *.zip *.acn *.glo *.ist *.epub *.glsdefs *.lot *.fls *.lof *.fdb_latexmk *.run.xml *.bcf /F
	GOTO :EOF

:realclean
	CALL make.bat clean
	DEL /Q %manuscript%.dvi -rf
	DEL /Q %manuscript%.pdf /F
	GOTO :EOF

:%.ps 
	CALL make.bat %.eps
	convert $< $@
	GOTO :EOF

:%.png 
	CALL make.bat %.eps
	convert $< $@
	GOTO :EOF

:zip
	zip paper.zip *.tex *.eps *.bib
	GOTO :EOF

:error
    IF "%1"=="" (
        ECHO make: *** No targets specified and no makefile found.  Stop.
    ) ELSE (
        ECHO make: *** No rule to make target '%1%'. Stop.
    )
    GOTO :EOF
