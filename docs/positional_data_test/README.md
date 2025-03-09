I captured these dumps to understand how to best capture positional data for class splits and wave arounds. These are three dumps to demonstrate how values captured change (or do not change):
* 01: Opening lap, I am last in my class, with the slower class right behind me.
* 02: Same lap, I let 2-3 cars of the slower class over take me.
* 03: We crossed S/F line, same order as 02.

What you will note:
* The `ResultsPositions` array does not update my current position information until I cross S/F. I.e. this is not a reliable source when figuring out detailed real time position information.
* Use `CarIdxLap` and `CarIdxLapDistPct` instead (like we have already been doing in the generator).