import numpy as np
import matplotlib.pyplot as plt
import kplr
client = kplr.API()
import pyfits
import glob
from Kepler_ACF import corr_run

def get_data(id):
    fnames = glob.glob("/Users/angusr/.kplr/data/lightcurves/00%s/*" % id)
    hdulist = pyfits.open(fnames[0])
    t = hdulist[1].data
    time = t["TIME"]
    flux = t["PDCSAP_FLUX"]
    flux_err = t["PDCSAP_FLUX_ERR"]
    q = t["SAP_QUALITY"]
    m = np.isfinite(time) * np.isfinite(flux) * np.isfinite(flux_err) * (q==0)
    x = time[m]
    med = np.median(flux[m])
    y = flux[m]/med - 1
    yerr = flux_err[m]/med
    for fname in fnames[1:]:
        hdulist = pyfits.open(fname)
        t = hdulist[1].data
        time = t["TIME"]
        flux = t["PDCSAP_FLUX"]
        flux_err = t["PDCSAP_FLUX_ERR"]
        q = t["SAP_QUALITY"]
        m = np.isfinite(time) * np.isfinite(flux) * np.isfinite(flux_err) * (q==0)
        x = np.concatenate((x, time[m]))
        med = np.median(flux[m])
        y = np.concatenate((y, flux[m]/med - 1))
        yerr = np.concatenate((yerr, flux_err[m]/med))
    return x, y, yerr

def bin_data(x, y, yerr, npts):
    mod, nbins = len(x) % npts, len(x) / npts
    if mod != 0:
        x, y, yerr = x[:-mod], y[:-mod], yerr[:-mod]
    xb, yb, yerrb = [np.zeros(nbins) for i in range(3)]
    for i in range(npts):
        xb += x[::npts]
        yb += y[::npts]
        yerrb += yerr[::npts]**2
        x, y, yerr = x[1:], y[1:], yerr[1:]
    return xb/npts, yb/npts, yerrb**.5/npts

def fit(x, y, yerr, id, p_init, plims, burnin=500, run=1500, npts=48,
        cutoff=100, sine_kernel=False, acf=False):
    """
    takes x, y, yerr and initial guesses and priors for period and does
    the full GP MCMC.
    Tuning parameters include cutoff (number of days), npts (number of points
    per bin).
    """

    # measure ACF period
    if acf:
        corr_run(x, y, yerr, id, "/Users/angusr/Python/GProtation/kepler452b")

    if sine_kernel:
        print "sine kernel"
        theta_init = [1., 1., 1., 1., 15.]
        from GProtation import MCMC, make_plot
    else:
        print "cosine kernel"
        theta_init = [1e-2, 1., 1e-2, 15.]
        print "theta_init = ", np.log(theta_init)
        from GProtation_cosine import MCMC, make_plot

    xb, yb, yerrb = bin_data(x, y, yerr, npts)  # bin data
    m = xb < cutoff  # truncate

    plt.clf()
    plt.errorbar(xb[m], yb[m], yerr=yerrb[m], fmt="k.", capsize=0)
    plt.savefig("lc")

    theta_init = np.log(theta_init)
    DIR = "cosine"
    if sine_kernel:
        DIR = "sine"

    sampler = MCMC(theta_init, xb[m], yb[m], yerrb[m], plims, burnin, run, id,
                   DIR)
    m = x < cutoff
    mcmc_result = make_plot(sampler, x[m], y[m], yerr[m], id, DIR, traces=True)

if __name__ == "__main__":
    id = "8311864"
    x, y, yerr = np.genfromtxt("%s_lc.txt" % id).T
    x -= x[0]

    cutoff = 100

    # initialise with acf
    corr_run(x, y, yerr, id, "acf")
    p_init = np.genfromtxt("acf/%s_result.txt" % id)
    print p_init

    plims = [p_init[0]*.7, p_init[0]*1.5]
    fit(x, y, yerr, id, p_init[0], plims, burnin=500, run=1500, npts=48,
            cutoff=cutoff, sine_kernel=False, acf=False)
