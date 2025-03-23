import argparse
import os
import ROOT
import csv
import pandas as pd
from datetime import date

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kError
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--run", type=int, required=True, help="Run number")
parser.add_argument("--noiseFreq", type=int, required=False, default =0, help="Frequency column value")
parser.add_argument("--csv", type=str, required=False, default="hist_means.csv", help="CSV file to save results.")
parser.add_argument("-f", "--fast", action="store_true", help="Make only configured plots; do not use --skip with this option")
parser.add_argument("-s", "--skip", action="store_true", default=False, help="Skip full 'plot loop' run only other functions",)
args = parser.parse_args()

runNumber = args.run
fast = args.fast
skip = args.skip
csvName = args.csv
noiseFreq = args.noiseFreq


def main():
    inputFileName = f"Results/Run_{runNumber}/Results.root"
    baseDirectoryPath = "Detector/Board_0"
    outputBaseDir = f"Plots/Run_{runNumber}"

    rootFile = ROOT.TFile.Open(inputFileName, "READ")
    if not rootFile or rootFile.IsZombie():
        print(f"Error: Cannot open {inputFileName}")
        return

    baseDirectory = rootFile.Get(baseDirectoryPath)
    if not baseDirectory or not baseDirectory.InheritsFrom("TDirectory"):
        print(
            f"Error: Target directory {baseDirectoryPath} not found in {inputFileName}"
        )
        return
    os.makedirs(outputBaseDir, exist_ok=True)

    # Loop through all subdirectories; plotting functions called from within looper
    mainLooper(baseDirectory, outputBaseDir)
    
    rootFile.Close()

def mainLooper(baseDirectory, outputBaseDir):
    allMods = []
    allHybrids = [] # store list of all hybrids and modules to avoid relooping

    # Loop over modules
    modules = getSubdirectories(baseDirectory, "OpticalGroup_")
    for module in modules:
        allMods.append(module)
        moduleOutputDir = os.path.join(outputBaseDir, module.GetName())
        os.makedirs(moduleOutputDir, exist_ok=True)
        # Plot module level hists
        for key in module.GetListOfKeys():
            if skip != True:
                configuredPlot(key.ReadObj(), moduleOutputDir)
        ### Func: Produce pixel noise heatmap for both hrbyids on a given module
        #drawModuleNoiseMap(module, moduleOutputDir)
        
        # Loop over hybrids
        hybrids = getSubdirectories(module, "Hybrid_")
        for hybrid in hybrids:
            allHybrids.append(hybrid)
            hybridOutputDir = os.path.join(moduleOutputDir, hybrid.GetName())
            os.makedirs(hybridOutputDir, exist_ok=True)
            # Plot hybrid level hists
            for key in hybrid.GetListOfKeys():
                if skip != True:
                    configuredPlot(key.ReadObj(), hybridOutputDir)

            # Loop over strips
            strips = getSubdirectories(hybrid, "SSA_")
            for strip in strips:
                stripOutputDir = os.path.join(hybridOutputDir, strip.GetName())
                os.makedirs(stripOutputDir, exist_ok=True)
                # Plot strip level hists
                for key in strip.GetListOfKeys():
                    if skip != True:
                        configuredPlot(key.ReadObj(), stripOutputDir)
            # Loop over pixels
            pixels = getSubdirectories(hybrid, "MPA_")
            for pixel in pixels:
                pixelOutputDir = os.path.join(hybridOutputDir, pixel.GetName())
                os.makedirs(pixelOutputDir, exist_ok=True)
                # Plot pixel level hists
                for key in pixel.GetListOfKeys():
                    if skip != True:
                        configuredPlot(key.ReadObj(), pixelOutputDir)

    exportHybridNoise(allHybrids, "HybridNoise", "noiseData.csv", noiseFreq)
    print("Done!")

def getSubdirectories(directory, pattern):
    matchedDirs = []
    for key in directory.GetListOfKeys():
        obj = key.ReadObj()
        if (obj.IsA().InheritsFrom("TDirectory")) and (pattern in obj.GetName()):
            matchedDirs.append(obj)
    return matchedDirs

def plot1DHistogram(
    hist, outputDir, title=None, xLabel=None, yLabel=None, filename=None
):
    canvas = ROOT.TCanvas("c1", "Canvas for 1D Histogram", 800, 600)
    if title:
        hist.SetTitle(f'Run {runNumber}: {title}')
    if xLabel:
        hist.GetXaxis().SetTitle(xLabel)
    if yLabel:
        hist.GetYaxis().SetTitle(yLabel)

    hist.SetLineColor(ROOT.kBlue)
    hist.SetLineWidth(2)
    hist.Draw()
    if filename is None:
        filename = hist.GetName().replace("(", "").replace(")", "")
    canvas.SaveAs(os.path.join(outputDir, f"{filename}.png"))
    canvas.Close()

def plot2DHistogram(
        hist, outputDir, title=None, xLabel=None, yLabel=None, zLabel=None, filename=None
):
    canvas = ROOT.TCanvas("c2", "Canvas for 2D Histogram", 800, 600)
    canvas.SetRightMargin(.14);
    if title:
        hist.SetTitle(f'Run {runNumber}: {title}')
    if xLabel:
        hist.GetXaxis().SetTitle(xLabel)
    if yLabel:
        hist.GetYaxis().SetTitle(yLabel)
    if zLabel:
        hist.GetZaxis().SetTitle(zLabel)

    hist.SetStats(0)
    hist.Draw("COLZ")
    if filename is None:
        filename = hist.GetName().replace("(", "").replace(")", "")
    canvas.SaveAs(os.path.join(outputDir, f"{filename}.png"))
    canvas.Close()

def configuredPlot(obj, outputDir):
    histName = obj.GetName()
    options = {}
    for pattern, opts in histConfig.items():
        if pattern in histName:
            options = opts
            break
    if (options == {}) and (fast is True):
        return
    title = options.get("title", histName)
    xLabel = options.get("x_label", None)
    yLabel = options.get("y_label", None)
    zLabel = options.get("z_label", None)
    if obj.InheritsFrom("TH1"):
        if obj.InheritsFrom("TH2"):
            plot2DHistogram(
                obj, outputDir, title=title, xLabel=xLabel, yLabel=yLabel, zLabel=zLabel
            )
        else:
            plot1DHistogram(
                obj, outputDir, title=title, xLabel=xLabel, yLabel=yLabel
            )

def drawModuleNoiseMap(module, outputDir):
    numHybrids = 2  # Two hybrids per module (rows)
    numMPAs = 8  # Eight MPAs per hybrid (columns)
    histWidth, histHeight = 300, 600  # Per histogram

    # Canvas size, adding extra padding
    marginX = 0.07  # 10% margin on left/right
    marginY = 0.05  # 5% margin on top/bottom
    canvasWidth = int(numMPAs * histWidth * (1 + 2 * marginX)+50)
    canvasHeight = int(numHybrids * histHeight * (1 + 2 * marginY) + 50)  # Extra for title

    canvas = ROOT.TCanvas("c_moduleNoise", "Module Noise Map", canvasWidth, canvasHeight)
    ROOT.gStyle.SetOptTitle(0)  # Disable individual histogram titles

    minVal, maxVal = float("inf"), float("-inf")
    noiseMaps = [[None] * numMPAs for _ in range(numHybrids)]  # 2D array to hold histograms

    print(f"Processing module: {module.GetName()}")

    # Loop over hybrids
    hybrids = getSubdirectories(module, "Hybrid_")  # Fixed function name
    if len(hybrids) != numHybrids:
        print("Warning: Expected 2 hybrids, found:", len(hybrids))

    for hybridIndex, hybrid in enumerate(hybrids):
        print(f"Processing Hybrid: {hybrid.GetName()}")

        # Loop over MPAs
        mpas = getSubdirectories(hybrid, "MPA_")  # Fixed function name
        if len(mpas) != numMPAs:
            print("Warning: Expected 8 MPAs per hybrid, found:", len(mpas))

        for mpaIndex, mpa in enumerate(mpas):
            print(f"  -> Found MPA: {mpa.GetName()}")

            # Find the 2DPixelNoise histogram
            for key in mpa.GetListOfKeys():
                hist = key.ReadObj()
                if hist.InheritsFrom("TH2") and "2DPixelNoise" in hist.GetName():
                    print(f"    -> Found 2DPixelNoise: {hist.GetName()}")

                    histMin = hist.GetMinimum()
                    histMax = hist.GetMaximum()
                    minVal = min(minVal, histMin)
                    maxVal = max(maxVal, histMax)

                    # Determine the correct placement based on counting order
                    if hybridIndex == 0:
                        noiseMaps[0][mpaIndex] = hist  # Bottom row: Left  Right
                    else:
                        noiseMaps[1][numMPAs - 1 - mpaIndex] = hist  # Top row: Right  Left

    # If no histograms were found, exit
    if all(all(cell is None for cell in row) for row in noiseMaps):
        print("No 2DPixelNoise histograms found!")
        return

    print(f"Global Min: {minVal}, Global Max: {maxVal}")

    # Define the start positions for centering
    gridLeft = marginX
    gridBottom = marginY
    gridTop = 1 - marginY

    padWidth = (1 - 2 * marginX) / numMPAs
    padHeight = (gridTop - gridBottom) / numHybrids

    # Draw histograms in their respective locations
    for row in range(numHybrids):
        for col in range(numMPAs):
            hist = noiseMaps[row][col]
            if hist is None:
                continue

            left = gridLeft + col * padWidth
            right = gridLeft + (col + 1) * padWidth
            top = gridTop - row * padHeight
            bottom = gridTop - (row + 1) * padHeight

            padName = f"pad_{row}_{col}"
            pad = ROOT.TPad(padName, padName, left, bottom, right, top)
            pad.SetMargin(0, 0.0, 0.025, 0.025)  # Small gap for row separation
            pad.Draw()
            pad.cd()

            hist.SetStats(0)
            hist.GetZaxis().SetRangeUser(minVal, 6)  # Apply uniform color scale
            hist.GetXaxis().SetNdivisions(0)  # Remove X-axis labels
            hist.GetYaxis().SetNdivisions(0)  # Remove Y-axis labels
            hist.LabelsOption("B")
            # Add chip index number next to each histogram
            chipIndex = row * numMPAs + (col if row == 0 else numMPAs - 1 - col)
            if (chipIndex >= 8):
                hist.Draw("COLB")
            else:
                hist.Draw("COLB RY RX")

            canvas.cd()  # Return to main canvas
            label = ROOT.TLatex()
            label.SetTextSize(0.03)
            label.SetTextAlign(22)
            if chipIndex < 9:
                label.DrawLatexNDC(left + padWidth * 0.45, top - 0.92, str(chipIndex) )
            else:
                label.DrawLatexNDC(left + padWidth * 0.45, top + 0.46, str(chipIndex) )

    # Create a color bar with TPaletteAxis
    paletteAxis = ROOT.TPaletteAxis(0.94, 0.06, 0.96, 0.94, 0, 6)
    
    paletteAxis.SetNdivisions(6)
    paletteAxis.SetLabelSize(0.025)
    paletteAxis.SetTickLength(0.015)
    paletteAxis.Draw()

    ROOT.gPad.Update()
    ROOT.gPad.RedrawAxis()

    # Add a global title
    canvas.cd()
    title = ROOT.TLatex()
    title.SetTextSize(0.03)
    title.SetTextAngle(90)
    title.DrawLatexNDC(0.06, 0.4, "Module Noise Map")

    # Save the canvas
    canvas.Modified()
    canvas.Update()
    canvas.SaveAs(os.path.join(outputDir, "Module_NoiseMap.png"))
    canvas.Close()

def exportHybridNoise(hybridList, histName, csvFile, freq):
    means = [runNumber, date.today().strftime("%m/%d/%Y"), "WARM", "Sine", freq, 1.2, 11.5]
    
    print(f"Extracting means for histogram: {histName}")
    hybridNumbers = []
    hybridData = {}
    
    for hybridIndex, hybrid in enumerate(hybridList):
        hybridNum = hybrid.GetName()[7:]
        if hybridNum == '2': continue
        hybridNumbers.append(hybridNum)
        
        histMean = None
        for key in hybrid.GetListOfKeys():
            hist = key.ReadObj()
            if hist.InheritsFrom("TH1F") and histName in hist.GetName():
                histMean = hist.GetMean()
                print(f"{hist.GetName()}, Mean: {histMean:.3f}")
                break
        if histMean is None:
            histMean = ""
        
        hybridData[hybridNum] = f'{histMean:.3f}'
    
    if os.path.isfile(csvFile):
        df = pd.read_csv(csvFile, dtype=str)
    else:
        df = pd.DataFrame(columns=["RunNumber", "Date", "Temperature", "Noise Form", "Frequency", "Amplitude", "LV Power"])
    
    for hybridNum in hybridNumbers:
        if f'Hybrid {hybridNum}' not in df.columns:
            df.insert(len(df.columns),f'Hybrid {hybridNum}', "")
    
    # stage new row
    newRow = {col: "" for col in df.columns}
    for i, value in enumerate(means):
        newRow[df.columns[i]] = value  
    for hybridNum, value in hybridData.items():
        newRow[f'Hybrid {hybridNum}'] = value 
    
    newRow_df = pd.DataFrame([newRow])
    df = pd.concat([df, newRow_df], ignore_index=True)

    # sort
    hybridColumns = sorted([col for col in df.columns if col.startswith('Hybrid')], key=lambda x: int(x.split()[1]))
    orderedColumns = list(df.columns[:7]) + hybridColumns
    df = df[orderedColumns]
    
    df.to_csv(csvFile, index=False)
    
    print(f"Data written to {csvFile}")

    
histConfig = {
    "SCurve_Chip": {"x_label": "Channel Number", "y_label": "Threshold", "z_label": "Occupancy"},
    # "histogram_name_pattern": {"title": "Histogram 1", "x_label": "X-Axis", "y_label": "Y-Axis"},
}

if __name__ == "__main__":
    main()
