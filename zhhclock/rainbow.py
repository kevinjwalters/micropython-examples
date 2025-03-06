### This is a Python version of Haochen Xie's Java code in
### https://stackoverflow.com/questions/1472514/convert-light-frequency-to-rgb

### Copyright (c) 2013 Chris Wyman, Peter-Pike Sloan, Peter Shirley
### Copyright (c) 2016 Haochen Xie
### Copyright (c) 2025 Kevin J. Walters


import math


def wavelengthToRGBtuple(wavelength):
    """Convert a wavelength in the visible light spectrum to a RGB color value that is suitable to be displayed on a
 * monitor
 *
 * @param wavelength wavelength in nm
 * @return RGB color encoded in a tuple values ranging [0.0, 1.0]."""
    return srgbXYZ2RGB(cie1931WavelengthToXYZFit(wavelength))


def srgbXYZ2RGB(xyz):
    """Convert XYZ to RGB in the sRGB color space
 * <p>
 * The conversion matrix and color component transfer function is taken from http://www.color.org/srgb.pdf, which
 * follows the International Electrotechnical Commission standard IEC 61966-2-1 "Multimedia systems and equipment -
 * Colour measurement and management - Part 2-1: Colour management - Default RGB colour space - sRGB"
 *
 * @param xyz XYZ values in a double array in the order of X, Y, Z. each value in the range of [0.0, 1.0]
 * @return RGB values in a double array, in the order of R, G, B. each value in the range of [0.0, 1.0]"""

    x = xyz[0]
    y = xyz[1]
    z = xyz[2]

    rl =  3.2406255 * x + -1.537208  * y + -0.4986286 * z
    gl = -0.9689307 * x +  1.8757561 * y +  0.0415175 * z
    bl =  0.0557101 * x + -0.2040211 * y +  1.0569959 * z

    return (srgbXYZ2RGBPostprocess(rl),
            srgbXYZ2RGBPostprocess(gl),
            srgbXYZ2RGBPostprocess(bl))


def srgbXYZ2RGBPostprocess(c):
    """helper function for {@link #srgbXYZ2RGB(double[])}"""
    ### clip if c is out of range
    c = 1 if c > 1 else (0 if c < 0 else c)

    ### apply the color component transfer function
    c = c * 12.92 if c <= 0.0031308 else 1.055 * math.pow(c, 1.0 / 2.4) - 0.055
    return c


def cie1931WavelengthToXYZFit(wavelength):
    """A multi-lobe, piecewise Gaussian fit of CIE 1931 XYZ Color Matching Functions by Wyman el al. from Nvidia. The
 * code here is adopted from the Listing 1 of the paper authored by Wyman et al.
 * <p>
 * Reference: Chris Wyman, Peter-Pike Sloan, and Peter Shirley, Simple Analytic Approximations to the CIE XYZ Color
 * Matching Functions, Journal of Computer Graphics Techniques (JCGT), vol. 2, no. 2, 1-11, 2013.
 *
 * @param wavelength wavelength in nm
 * @return XYZ in a double array in the order of X, Y, Z. each value in the range of [0.0, 1.0]"""
    wave = wavelength

    t1 = (wave - 442.0) * (0.0624 if wave < 442.0 else 0.0374)
    t2 = (wave - 599.8) * (0.0264 if (wave < 599.8) else 0.0323)
    t3 = (wave - 501.1) * (0.0490 if (wave < 501.1) else 0.0382)
    x = (  0.362 * math.exp(-0.5 * t1 * t1)
         + 1.056 * math.exp(-0.5 * t2 * t2)
         - 0.065 * math.exp(-0.5 * t3 * t3))

    t1 = (wave - 568.8) * (0.0213 if (wave < 568.8) else 0.0247)
    t2 = (wave - 530.9) * (0.0613 if (wave < 530.9) else 0.0322)
    y = (  0.821 * math.exp(-0.5 * t1 * t1)
         + 0.286 * math.exp(-0.5 * t2 * t2))

    t1 = (wave - 437.0) * (0.0845 if (wave < 437.0) else 0.0278)
    t2 = (wave - 459.0) * (0.0385 if (wave < 459.0) else 0.0725)
    z = (  1.217 * math.exp(-0.5 * t1 * t1)
         + 0.681 * math.exp(-0.5 * t2 * t2))

    return (x, y, z)
