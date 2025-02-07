import h5py
import numpy as np
import scipy.constants as ct
from astropy.io import ascii
import os
import pickle


def read_out_to_hdf5(output_string, input_dict, output, test_freqs, test_pdots):
    with h5py.File(output_string + ".hdf5", "w") as f:
        f.create_dataset(
            "P_test",
            shape=test_freqs.shape,
            dtype=test_freqs.dtype,
            data=1.0 / test_freqs,
            chunks=True,
            compression="gzip",
            compression_opts=9,
        )
        f.create_dataset(
            "Pdot_test",
            shape=test_pdots.shape,
            dtype=test_pdots.dtype,
            data=test_pdots,
            chunks=True,
            compression="gzip",
            compression_opts=9,
        )
        f.create_dataset(
            "Pdot_true",
            shape=input_dict["Pdot"].shape,
            dtype=input_dict["Pdot"].dtype,
            data=input_dict["Pdot"],
            chunks=True,
            compression="gzip",
            compression_opts=9,
        )
        f.create_dataset(
            "P0_true",
            shape=input_dict["period"].shape,
            dtype=input_dict["period"].dtype,
            data=input_dict["period"],
            chunks=True,
            compression="gzip",
            compression_opts=9,
        )
        f.create_dataset(
            "ce_vals",
            shape=output.shape,
            dtype=output.dtype,
            data=output,
            chunks=True,
            compression="gzip",
            compression_opts=9,
        )
    print("Read out data to {}.hdf5".format(output_string))
    return


def read_in_from_hdf5(input_string):
    with h5py.File(input_string + ".hdf5", "r") as f:
        keys = list(f)
        ce_val_dict = {key: f[key][:] for key in keys}
    print("Read in data from {}.hdf5".format(input_string))
    print("Keys are", keys)
    return ce_val_dict


def read_helper(fp):
    # add new routines as necessary
    if fp[-4:] == ".txt" or fp[-4:] == ".csv":
        data = np.asarray(ascii.read(fp))
        keys = data.dtype.names

    params = {key: data[key] for key in keys}
    if "q" not in keys:
        m1 = data["m1"]
        m2 = data["m2"]
        params["q"] = m1 / m2 * (m1 >= m2) + m2 / m1 * (m1 < m2)

    return params


def cosmic_read_helper(fp, x_sun=0.0, y_sun=0.0, z_sun=0.0, use_gr=False):
    data = np.asarray(ascii.read(fp))
    keys = data.dtype.names

    params = {key: data[key] for key in keys}
    params["m1"] = m1 = params["m1 [msun]"]
    params["m2"] = m2 = params["m2[msun]"]
    params["q"] = q = m1 / m2 * (m1 >= m2) + m2 / m1 * (m1 < m2)
    params["m_tot"] = m1 + m2

    params["d"] = 1e3 * (
        (params["xGx[kpc]"] - x_sun) ** 2
        + (params["yGx[kpc]"] - y_sun) ** 2
        + (params["zGx[kpc]"] - z_sun) ** 2
    ) ** (1 / 2)
    P0_sec = 2.0 / params["f_gw[Hz]"]
    params["period"] = P0_sec / (3600.0 * 24.0)

    if use_gr is False:
        fdot_gw = params["f_dot_total [yr^(-2)]"] / ct.Julian_year ** 2
        params["Pdot"] = -1.0 / 2.0 * fdot_gw * P0_sec ** 2

    params["incl"] = np.ones_like(params["period"]) * 100.0
    params["sbratio"] = np.ones_like(params["period"]) * 0.5
    return params


def LSST_read_in(folder, start=None, end=None):
    # open a file, where you stored the pickled data
    if folder[-1] != "/":
        folder = folder + "/"
    lcs_out = []

    if start is None:
        start = 0
    if end is None:
        end = 1323

    for i in range(start, end):
        fp = "ellc_OpSim1520_%04d.pickle" % i
        print(fp)
        fid = open(folder + fp, "rb")
        # dump information to that file
        ls = pickle.load(fid)
        # close the file
        fid.close()

        for ii, lkey in enumerate(ls.keys()):
            l = ls[lkey]
            if ii == 0:
                hjd, mag, magerr = (
                    l["OpSimDates"],
                    l["magObs"] - np.median(l["magObs"]),
                    l["e_magObs"],
                )
            else:
                hjd = np.hstack((hjd, l["OpSimDates"]))
                mag = np.hstack((mag, l["magObs"] - np.median(l["magObs"])))
                magerr = np.hstack((magerr, l["e_magObs"]))

        hjd, mag, magerr = np.array(hjd), np.array(mag), np.array(magerr)
        fid = np.ones(hjd.shape)

        hjd = hjd - np.min(hjd)

        print(np.min(hjd), np.max(hjd))

        lightcurve = np.array([hjd, mag]).T

        lcs_out.append(lightcurve)

    real_periods = np.load("LC/true_periods.npy")[start:end]
    return lcs_out, real_periods
