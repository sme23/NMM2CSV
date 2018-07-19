import nightmare, sys, csv, glob, os

TABLE_INLINED = False

def showExceptionAndExit(exc_type, exc_value, tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    input("Press Enter key to exit.")
    sys.exit(-1)

def getArgLength(nmmentry):
    """takes the nmm entry object and returns the appropriate EA marker"""
    if (nmmentry.length==4) & (nmmentry.offset%4==0):
        return "WORD "
    elif (nmmentry.length==2) & (nmmentry.offset%2==0):
        return "SHORT "
    else:
        return "BYTE "

def addToInstaller(csvList,installername):
    """Takes a list of csv files and adds them to the EA installer"""
    with open(installername,"w") as myfile:
        myfile.write("//EA Table Installation file generated by c2ea.exe\n\n")
        myfile.write('#include "Table Definitions.txt"\n\n')

    for csv in csvList:
        nmpath = csv.replace(".csv",".nmm")
        nmm = nightmare.NightmareTable(nmpath)
        filename = csv.replace(".csv",".event") #I don't wanna use .txt because it conflicts, but this is supposed to be a text file!
        filename = filename.replace(os.getcwd()+'\\','')
        with open(installername,'a') as myfile:
            #myfile.write("ORG " + hex(nmm.offset) + '\n') Don't put the offset here, have it in the dmp.
            myfile.write('#include "' + filename + '"\n\n')

def process(inputCSV, inputNMM, filename, rom):
    """Takes a csv and spits out an EA macro file (.event, but actually text). Requires a nmm with the same name in the same folder.""" #is it possible to tell if it's inline?
    global TABLE_INLINED

    macroName = "_C2EA_{}".format(os.path.split(os.path.splitext(inputCSV)[0])[1].replace(os.path.sep, "_")).replace(' ', '_')

    nmm = nightmare.NightmareTable(inputNMM)
    rompath = rom
    macroArgs = [] #params for macro
    macroOutput = '' #expanded macro form
    outputlines = []
    originalOffset = nmm.offset
    tableOffset = originalOffset #this gets changed to whatever is in the first cell of the csv actually
    currlen = '' #because we start with BYTE
    fillwithzero = None

    for x in range(nmm.colNum):
        argx = "arg"+'{0:03d}'.format(x)
        macroArgs.append(argx) #arg000, arg001, arg002 etc up to 1000 columns.
        arglen = getArgLength(nmm.columns[x]) #this gets the appropriate length string.
        if arglen!=currlen: #only append if needed else just add arg.
            if currlen!='': #this should only be on the first line
                macroOutput+=';'
            #assuming arglen does not equal currlen
            macroOutput+=(arglen + argx + ' ')
            currlen = arglen
        else:
            macroOutput+=(argx + ' ')

    with open(inputCSV, 'r') as myfile:
        table = csv.reader(myfile)
        tableOffset = next(table)[0]
        for row in table:
            outputline = "{}(".format(macroName)
            items = zip(nmm.columns, row[1:])
            for entry, data in items:
                thisentry = ''
                #output.extend(int(data, 0).to_bytes(entry.length, 'little', signed=entry.signed))
                if data=='':
                    if fillwithzero == None:
                        fillwithzero = input("Warning: "+ inputCSV + " has a blank cell.\nContinue anyway? Fills cells with '0' (y/n)").strip().lower()=='y'
                    if fillwithzero==True:
                        data = '0'
                    else:
                        input("Press Enter to quit.")
                        sys.exit(-1)
                try:
                    arglen = getArgLength(entry)
                    if (arglen=="WORD ")|(arglen=="SHORT "):
                        outputline += data + ','
                    else:
                        dt = int(data, 0).to_bytes(entry.length, 'little', signed=entry.signed) #this is a string i guess
                        for byte in dt:
                            thisentry += (hex(byte)+' ')
                        outputline += thisentry[:-1] + ','
                except ValueError: #if it's not a number, just add it directly
                    outputline += (data+',')
            outputline = outputline[:-1] + ')'
            outputlines.append(outputline)

    with open(filename, 'w') as dumpfile:
        inline = False
        dumpfile.write("#define {}(".format(macroName))
        dumpfile.write(','.join(macroArgs)) #turns list into 'arg000,arg001' etc
        dumpfile.write(') "')
        dumpfile.write(macroOutput + '"\n\n') #e.g. BYTE arg000, WORD arg001, etc
        if tableOffset.strip()[0:6]=="INLINE":
            from c2eaPfinder import pointerOffsets
            TABLE_INLINED = True
            if rompath == None:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                from tkinter import filedialog
                rompath = filedialog.askopenfilename(filetypes=[("GBA files",".gba"),("All files",".*")],initialdir=os.getcwd(),title="Select ROM to use for repointing")
            label = tableOffset.replace("INLINE",'').strip()

            # Here we do *not* want to use PFinder

            dumpfile.write("PUSH\n")

            for offset in pointerOffsets(rompath, originalOffset | 0x8000000):
                dumpfile.write("ORG ${:X}\n".format(offset))
                dumpfile.write("POIN {}\n".format(label))

            dumpfile.write("POP\n")

            # There, much better :)

            dumpfile.write("ALIGN 4\n{}:\n".format(label))

            inline = True
        else:
            dumpfile.write("PUSH\nORG "+tableOffset+"\n")
        dumpfile.write('\n'.join(outputlines))
        if not inline:
                dumpfile.write("\nPOP")
        #dumpfile.write('\n}\n')
    print("Wrote to " + filename)
    return rompath


def main():
    sys.excepthook = showExceptionAndExit
    
    doSingleFile = False

    folder    = os.getcwd()
    installer = "Table Installer.event"
    
    rom       = None
    
    csvFile   = None
    nmmFile   = None
    outFile   = None

    if len(sys.argv) > 1:
        import argparse
        
        parser = argparse.ArgumentParser()
        
        # Common arguments
        parser.add_argument('rom', nargs='?')
        # parser.add_argument('-nocache') # sounds like no$ xd
        # parser.add_argument('-clearcache')
        
        # Arguments for single CSV processing
        parser.add_argument('-nmm')
        parser.add_argument('-csv')
        parser.add_argument('-out')

        # Arguments for folder processing
        parser.add_argument('-folder')
        parser.add_argument('-installer')
        
        args = parser.parse_args()
        
        rom = args.rom
        
        if args.folder != None:
            folder = args.folder
            
        installer = args.installer if args.installer != None else (folder + '/Table Installer.event')
        
        if args.csv != None:
            doSingleFile = True
            
            csvFile = args.csv
            nmmFile = args.nmm if args.nmm != None else csvFile.replace(".csv", ".nmm")
            outFile = args.out if args.out != None else csvFile.replace(".csv", ".event")
        
        elif (args.nmm != None) or (args.out != None):
            sys.exit("ERROR: -nmm or -out argument specified without -csv, aborting.")

    if doSingleFile:
        if not os.path.exists(csvFile):
            sys.exit("ERROR: CSV File `{}` doesn't exist!".format(csvFile))
        
        if not os.path.exists(nmmFile):
            sys.exit("ERROR: NMM File `{}` doesn't exist!".format(nmmFile))
        
        process(csvFile, nmmFile, outFile, rom)
    
    else: # not doSingleFile
        csvList = glob.glob(folder + '/**/*.csv', recursive = True)
        
        for filename in csvList:
            rom = process(
                filename,
                filename.replace(".csv",".nmm"),
                filename.replace(".csv",".event"),
                rom
            )
        
        addToInstaller(csvList, installer)
    
    if TABLE_INLINED:
        # If we ran successfully and used pfinder, save the pfinder cache.
        from c2eaPfinder import writeCache
        writeCache()
    
    input("Press Enter to continue")

if __name__ == '__main__':
    main()
