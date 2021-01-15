import glob
import ntpath


inputFolder = r'D:\KwDownload\song'
outputFoder = r'D:\KwDownload\lyc'

inputFiles = glob.glob(inputFolder + r'/' + r'*.lrc')

for file in inputFiles:
    print(file)
    try:
        with open(file, encoding="GB2312") as f:
            outFile = outputFoder + r'/' + ntpath.basename(file)
            print(outFile) 
            with open(outFile, 'w', encoding='utf-8') as of:
                of.write(f.read())
    except:
        pass