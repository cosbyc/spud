import argparse
import os

import ROOT

ROOT.gErrorIgnoreLevel = ROOT.kError
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--run", type=int, required=True, help="Run number")
parser.add_argument(
    "-f", "--fast", action="store_true", help="Make only configured plots"
)
parser.add_argument(
    "-s",
    "--skip",
    action="store_true",
    help="Skip full 'plot loop' run only other functions",
)
args = parser.parse_args()

runNumber = args.run
fast = args.fast
skip = args.skip

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

    # Make generic plots of all histograms
    if skip is not True:
        runAllHists(baseDirectory, outputBaseDir)

    # Add other plotting functions...

    rootFile.Close()

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
    hist, outputDir, title=None, xLabel=None, yLabel=None, filename=None
):
    canvas = ROOT.TCanvas("c2", "Canvas for 2D Histogram", 800, 600)
    if title:
        hist.SetTitle(f'Run {runNumber}: {title}')
    if xLabel:
        hist.GetXaxis().SetTitle(xLabel)
    if yLabel:
        hist.GetYaxis().SetTitle(yLabel)

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
    if obj.InheritsFrom("TH1"):
        if obj.InheritsFrom("TH2"):
            plot2DHistogram(
                obj, outputDir, title=title, xLabel=xLabel, yLabel=yLabel
            )
        else:
            plot1DHistogram(
                obj, outputDir, title=title, xLabel=xLabel, yLabel=yLabel
            )

def runAllHists(baseDirectory, outputBaseDir):
    print("Making all plots...")
    # Loop over modules
    modules = getSubdirectories(baseDirectory, "OpticalGroup_")
    for module in modules:

        moduleOutputDir = os.path.join(outputBaseDir, module.GetName())
        os.makedirs(moduleOutputDir, exist_ok=True)

        # Plot module level hists
        for key in module.GetListOfKeys():
            configuredPlot(key.ReadObj(), moduleOutputDir)

        # Loop over hybrids
        hybrids = getSubdirectories(module, "Hybrid_")
        for hybrid in hybrids:

            hybridOutputDir = os.path.join(moduleOutputDir, hybrid.GetName())
            os.makedirs(hybridOutputDir, exist_ok=True)

            # Plot hybrid level hists
            for key in hybrid.GetListOfKeys():
                configuredPlot(key.ReadObj(), hybridOutputDir)

            # Loop over strips
            strips = getSubdirectories(hybrid, "SSA_")
            for strip in strips:

                stripOutputDir = os.path.join(hybridOutputDir, strip.GetName())
                os.makedirs(stripOutputDir, exist_ok=True)

                # Plot strip level hists
                for key in strip.GetListOfKeys():
                    configuredPlot(key.ReadObj(), stripOutputDir)

            # Loop over pixels
            pixels = getSubdirectories(hybrid, "MPA_")
            for pixel in pixels:

                pixelOutputDir = os.path.join(hybridOutputDir, pixel.GetName())
                os.makedirs(pixelOutputDir, exist_ok=True)

                # Plot pixel level hists
                for key in pixel.GetListOfKeys():
                    configuredPlot(key.ReadObj(), pixelOutputDir)
    print("Done!")

histConfig = {
    "SCurve_Chip": {"x_label": "Channel Number", "y_label": "Threshold"},
    # "histogram_name_pattern": {"title": "Histogram 1", "x_label": "X-Axis", "y_label": "Y-Axis"},
}

if __name__ == "__main__":
    main()
