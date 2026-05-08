PDF=main.pdf
TEX=main.tex

all:
	pdflatex $(TEX)
	bibtex main || exit 0
	pdflatex $(TEX)
	pdflatex $(TEX)

clean:
	del /Q *.aux *.bbl *.blg *.log *.out *.toc 2>NUL || exit 0
