"""
data reader for LUDB
"""
import os
import json
from collections import namedtuple
from datetime import datetime
from typing import Union, Optional, Any, List, Tuple, Sequence, NoReturn
from numbers import Real

import numpy as np
import pandas as pd
import wfdb
from easydict import EasyDict as ED

from ..utils.common import (
    ArrayLike,
    get_record_list_recursive,
)


__all__ = [
    "LUDBReader",
]


ECGWaveForm = namedtuple(
    typename='ECGWaveForm',
    field_names=['name', 'onset', 'offset', 'peak', 'duration'],
)


class LUDB(PhysioNetDataBase):
    """ NOT Finished, 

    Lobachevsky University Electrocardiography Database

    ABOUT ludb:
    -----------
    1. consist of 200 10-second conventional 12-lead (i, ii, iii, avr, avl, avf, v1, v2, v3, v4, v5, v6) ECG signal records, with sampling frequency 500 Hz
    2. boundaries of P, T waves and QRS complexes were manually annotated by cardiologists, and with the corresponding diagnosis
    3. annotated are 16797 P waves, 21966 QRS complexes, 19666 T waves (in total, 58429 annotated waves)
    4. distributions of data:
        4.1. rhythm distribution:
            Rhythms	                        Number of ECGs
            Sinus rhythm	                143
            Sinus tachycardia	            4
            Sinus bradycardia	            25
            Sinus arrhythmia	            8
            Irregular sinus rhythm	        2
            Abnormal rhythm	                19
        4.2. electrical axis distribution:
            Heart electric axis	            Number of ECGs
            Normal	                        75
            Left axis deviation (LAD)	    66
            Vertical	                    26
            Horizontal	                    20
            Right axis deviation (RAD)	    3
            Undetermined	                10
        4.3. distribution of records with conduction abnomalities (totally 79):
            Conduction abnormalities	                        Number of ECGs
            Sinoatrial blockade, undetermined	                1
            I degree AV block	                                10
            III degree AV-block	                                5
            Incomplete right bundle branch block	            29
            Incomplete left bundle branch block	                6
            Left anterior hemiblock	                            16
            Complete right bundle branch block	                4
            Complete left bundle branch block	                4
            Non-specific intravintricular conduction delay	    4
        4.4. distribution of records with extrasystoles (totally 35):
            Extrasystoles	                                                    Number of ECGs
            Atrial extrasystole, undetermined	                                2
            Atrial extrasystole, low atrial	                                    1
            Atrial extrasystole, left atrial	                                2
            Atrial extrasystole, SA-nodal extrasystole	                        3
            Atrial extrasystole, type: single PAC	                            4
            Atrial extrasystole, type: bigemini	                                1
            Atrial extrasystole, type: quadrigemini	                            1
            Atrial extrasystole, type: allorhythmic pattern	                    1
            Ventricular extrasystole, morphology: polymorphic	                2
            Ventricular extrasystole, localisation: RVOT, anterior wall	        3
            Ventricular extrasystole, localisation: RVOT, antero-septal part	1
            Ventricular extrasystole, localisation: IVS, middle part	        1
            Ventricular extrasystole, localisation: LVOT, LVS	                2
            Ventricular extrasystole, localisation: LV, undefined	            1
            Ventricular extrasystole, type: single PVC	                        6
            Ventricular extrasystole, type: intercalary PVC	                    2
            Ventricular extrasystole, type: couplet	                            2
        4.5. distribution of records with hypertrophies (totally 253):
            Hypertrophies	                    Number of ECGs
            Right atrial hypertrophy	        1
            Left atrial hypertrophy	            102
            Right atrial overload	            17
            Left atrial overload	            11
            Left ventricular hypertrophy	    108
            Right ventricular hypertrophy	    3
            Left ventricular overload	        11
        4.6. distribution of records of pacing rhythms (totally 12):
            Cardiac pacing	                Number of ECGs
            UNIpolar atrial pacing	        1
            UNIpolar ventricular pacing	    6
            BIpolar ventricular pacing	    2
            Biventricular pacing	        1
            P-synchrony	                    2
        4.7. distribution of records with ischemia (totally 141):
            Ischemia	                                            Number of ECGs
            STEMI: anterior wall	                                8
            STEMI: lateral wall	                                    7
            STEMI: septal	                                        8
            STEMI: inferior wall	                                1
            STEMI: apical	                                        5
            Ischemia: anterior wall	                                5
            Ischemia: lateral wall	                                8
            Ischemia: septal	                                    4
            Ischemia: inferior wall	                                10
            Ischemia: posterior wall	                            2
            Ischemia: apical	                                    6
            Scar formation: lateral wall	                        3
            Scar formation: septal	                                9
            Scar formation: inferior wall	                        3
            Scar formation: posterior wall	                        6
            Scar formation: apical	                                5
            Undefined ischemia/scar/supp.NSTEMI: anterior wall	    12
            Undefined ischemia/scar/supp.NSTEMI: lateral wall	    16
            Undefined ischemia/scar/supp.NSTEMI: septal	            5
            Undefined ischemia/scar/supp.NSTEMI: inferior wall	    3
            Undefined ischemia/scar/supp.NSTEMI: posterior wall	    4
            Undefined ischemia/scar/supp.NSTEMI: apical	            11
        4.8. distribution of records with non-specific repolarization abnormalities (totally 85):
            Non-specific repolarization abnormalities	    Number of ECGs
            Anterior wall	                                18
            Lateral wall	                                13
            Septal	                                        15
            Inferior wall	                                19
            Posterior wall	                                9
            Apical	                                        11
        4.9. there are also 9 records with early repolarization syndrome
        there might well be records with multiple conditions.
    

    NOTE:
    -----

    ISSUES:
    -------
    1. (version 1.0.0) ADC gain might be wrong, either `units` should be μV, or `adc_gain` should be 1000 times larger

    Usage:
    ------
    1. ECG wave delineation
    2. ECG arrhythmia classification

    References:
    -----------
    [1] https://physionet.org/content/ludb/1.0.0/
    [2] Kalyakulina, A., Yusipov, I., Moskalenko, V., Nikolskiy, A., Kozlov, A., Kosonogov, K., Zolotykh, N., & Ivanchenko, M. (2020). Lobachevsky University Electrocardiography Database (version 1.0.0).
    """
    def __init__(self, db_dir:str, working_dir:Optional[str]=None, verbose:int=2, **kwargs):
        """
        Parameters:
        -----------
        db_dir: str,
            storage path of the database
        working_dir: str, optional,
            working directory, to store intermediate files and log file
        verbose: int, default 2,
        """
        super().__init__(db_name='ludb', db_dir=db_dir, working_dir=working_dir, verbose=verbose, **kwargs)
        self.freq = 500
        self.spacing = 1000 / self.freq
        self.data_ext = "dat"
        self.all_leads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6',]
        self.all_leads_lower = [l.lower() for l in self.all_leads]
        self.beat_ann_ext = [f"atr_{item}" for item in self.all_leads_lower]

        self._all_symbols = ['(', ')', 'N', 'p', 't']
        """
        this can be obtained using the following code:
        >>> data_gen = LUDB(db_dir="/home/wenhao71/data/PhysioNet/ludb/1.0.0/")
        >>> all_symbols = set()
        >>> for rec in data_gen.all_records:
        ...     for ext in data_gen.beat_ann_ext:
        ...         ann = wfdb.rdann(os.path.join(data_gen.db_dir, rec), extension=ext)
        ...         all_symbols.update(ann.symbol)
        """
        self._symbol_to_wavename = ED(N='qrs', p='pwave', t='twave')

        self._ls_rec()
    

    def get_subject_id(self, rec:str) -> int:
        """

        """
        raise NotImplementedError


    def load_data(self, rec:str, leads:Optional[Union[str, List[str]]]=None, data_format='channel_first', units:str='mV', freq:Optional[Real]=None) -> np.ndarray:
        """ finished, checked,

        load physical (converted from digital) ecg data,
        which is more understandable for humans

        Parameters:
        -----------
        rec: str,
            name of the record
        leads: str or list of str, optional,
            the leads to load
        data_format: str, default 'channel_first',
            format of the ecg data,
            'channel_last' (alias 'lead_last'), or
            'channel_first' (alias 'lead_first', original)
        units: str, default 'mV',
            units of the output signal, can also be 'μV', with an alias of 'uV'
        freq: real number, optional,
            if not None, the loaded data will be resampled to this frequency
        
        Returns:
        --------
        data: ndarray,
            the ecg data
        """
        assert data_format.lower() in ['channel_first', 'lead_first', 'channel_last', 'lead_last']
        if not leads:
            _leads = self.all_leads_lower
        elif isinstance(leads, str):
            _leads = [leads.lower()]
        else:
            _leads = [l.lower() for l in leads]
        
        rec_fp = os.path.join(self.db_dir, rec)
        wfdb_rec = wfdb.rdrecord(rec_fp, physical=True, channel_names=_leads)
        # p_signal of 'lead_last' format
        # ref. ISSUES 1.
        data = np.asarray(wfdb_rec.p_signal.T / 1000, dtype=np.float64)

        if units.lower() in ['uv', 'μv']:
            data = data * 1000

        if freq is not None and freq != self.freq:
            data = resample_poly(data, freq, self.freq, axis=1)

        if data_format.lower() in ['channel_last', 'lead_last']:
            data = data.T

        return data


    def load_ann(self, rec:str, leads:Optional[Sequence[str]]=None, metadata:bool=False) -> dict:
        """

        loading the wave delineation, along with metadata if specified

        Parameters:
        -----------
        rec: str,
            name of the record
        leads: str or list of str, optional,
            the leads to load
        metadata: bool, default False,
            if True, load metadata from corresponding head file

        Returns:
        --------
        ann_dict: dict,
        """
        ann_dict = ED()
        rec_fp = os.path.join(self.db_dir, rec)

        # wave delineation annotations
        _leads = leads or self.all_leads_lower
        _ann_ext = [f"atr_{item}" for item in _leads]
        ann_dict['waves'] = ED({l:[] for l in _leads})
        for l, e in zip(_leads, _ann_ext):
            ann = wfdb.rdann(rec_fp, extension=e)
            df_lead_ann = pd.DataFrame()
            symbols = np.array(ann.symbol)
            peak_inds = np.where(np.isin(symbols, ['p', 'N', 't']))[0]
            df_lead_ann['peak'] = ann.sample[peak_inds]
            df_lead_ann['onset'] = np.nan
            df_lead_ann['offset'] = np.nan
            for i, row in df_lead_ann.iterrows():
                peak_idx = peak_inds[i]
                if peak_idx == 0:
                    df_lead_ann.loc[i, 'onset'] = row['peak']
                    if symbols[peak_idx+1] == ')':
                        df_lead_ann.loc[i, 'offset'] = ann.sample[peak_idx+1]
                    else:
                        df_lead_ann.loc[i, 'offset'] = row['peak']
                elif peak_idx == len(symbols) - 1:
                    df_lead_ann.loc[i, 'offset'] = row['peak']
                    if symbols[peak_idx-1] == '(':
                        df_lead_ann.loc[i, 'onset'] = ann.sample[peak_idx-1]
                    else:
                        df_lead_ann.loc[i, 'onset'] = row['peak']
                else:
                    if symbols[peak_idx-1] == '(':
                        df_lead_ann.loc[i, 'onset'] = ann.sample[peak_idx-1]
                    else:
                        df_lead_ann.loc[i, 'onset'] = row['peak']
                    if symbols[peak_idx+1] == ')':
                        df_lead_ann.loc[i, 'offset'] = ann.sample[peak_idx+1]
                    else:
                        df_lead_ann.loc[i, 'offset'] = row['peak']
            # df_lead_ann['onset'] = ann.sample[np.where(symbols=='(')[0]]
            # df_lead_ann['offset'] = ann.sample[np.where(symbols==')')[0]]

            df_lead_ann['duration'] = (df_lead_ann['offset'] - df_lead_ann['onset']) * self.spacing
            
            df_lead_ann.index = symbols[peak_inds]

            for c in ['peak', 'onset', 'offset']:
                df_lead_ann[c] = df_lead_ann[c].values.astype(int)
            
            for _, row in df_lead_ann.iterrows():
                w = ECGWaveForm(
                    name=self._symbol_to_wavename[row.name],
                    onset=int(row.onset),
                    offset=int(row.offset),
                    peak=int(row.peak),
                    duration=row.duration,
                )
                ann_dict['waves'][l].append(w)

        if metadata:
            header_dict = self._load_header(rec)
            ann_dict.update(header_dict)
        
        return ann_dict


    def load_diagnoses(self, rec:str) -> List[str]:
        """ finished, checked,

        load diagnoses of the `rec`

        Parameters:
        -----------
        rec: str,
            name of the record

        Returns:
        --------
        diagnoses: list of str,
        """
        diagnoses = self._load_header(rec)['diagnoses']
        return diagnoses


    def _load_header(self, rec:str) -> dict:
        """ finished, checked,

        load header data into a dict

        Parameters:
        -----------
        rec: str,
            name of the record

        Returns:
        --------
        header_dict: dict,
        """
        header_dict = ED({})
        header_reader = wfdb.rdheader(rec_fp)
        header_dict['units'] = header_reader.units
        header_dict['baseline'] = header_reader.baseline
        header_dict['adc_gain'] = header_reader.adc_gain
        header_dict['record_fmt'] = header_reader.fmt
        try:
            header_dict['age'] = int([l for l in header_reader.comments if '<age>' in l][0].split(': ')[-1])
        except:
            header_dict['age'] = np.nan
        try:
            header_dict['sex'] = [l for l in header_reader.comments if '<sex>' in l][0].split(': ')[-1]
        except:
            header_dict['sex'] = ''
        d_start = [idx for idx, l in header_reader.comments if '<diagnoses>' in l][0] + 1
        header_dict['diagnoses'] = header_reader.comments[d_start:]
        return header_dict


    def plot(self, rec:str, data:Optional[np.ndarray]=None, ticks_granularity:int=0, leads:Optional[Union[str, List[str]]]=None, same_range:bool=False, waves:Optional[ECGWaveForm]=None, **kwargs) -> NoReturn:
        """ finished, checked, to improve,

        plot the signals of a record or external signals (units in μV),
        with metadata (freq, labels, tranche, etc.),
        possibly also along with wave delineations

        Parameters:
        -----------
        rec: str,
            name of the record
        data: ndarray, optional,
            12-lead ecg signal to plot,
            if given, data of `rec` will not be used,
            this is useful when plotting filtered data
        ticks_granularity: int, default 0,
            the granularity to plot axis ticks, the higher the more
        leads: str or list of str, optional,
            the leads to plot
        same_range: bool, default False,
            if True, forces all leads to have the same y range
        waves: ECGWaveForm, optional,
            the waves (p waves, t waves, qrs complexes)
        kwargs: dict,

        TODO:
        -----
        1. slice too long records, and plot separately for each segment
        2. plot waves using `axvspan`

        NOTE:
        -----
        `Locator` of `plt` has default `MAXTICKS` equal to 1000,
        if not modifying this number, at most 40 seconds of signal could be plotted once

        Contributors: Jeethan, and WEN Hao
        """
        if 'plt' not in dir():
            import matplotlib.pyplot as plt
            plt.MultipleLocator.MAXTICKS = 3000
        if leads is None or leads == 'all':
            _leads = self.all_leads_lower
        elif isinstance(leads, str):
            _leads = [leads.lower()]
        else:
            _leads = [l.lower() for l in leads]
            _leads = [l for l in self.all_leads_lower if l in leads]  # keep in order

        # lead_list = self.load_ann(rec)['df_leads']['lead_name'].tolist()
        # lead_indices = [lead_list.index(l) for l in leads]
        lead_indices = [self.all_leads_lower.index(l) for l in _leads]
        if data is None:
            _data = self.load_data(rec, data_format='channel_first', units='μV')[lead_indices]
        else:
            units = self._auto_infer_units(data)
            print(f"input data is auto detected to have units in {units}")
            if units.lower() == 'mv':
                _data = 1000 * data
            else:
                _data = data
        
        if same_range:
            y_ranges = np.ones((_data.shape[0],)) * np.max(np.abs(_data)) + 100
        else:
            y_ranges = np.max(np.abs(_data), axis=1) + 100

        if not data and not waves:
            waves = self.load_ann(rec, leads=_leads)['waves']

        if waves:
            p_waves, qrs, t_waves = [], [], []
            for w in waves:
                itv = [w.onset, w.offset]
                if w.name == self._symbol_to_wavename['p']:
                    p_waves.append(itv)
                elif w.name == self._symbol_to_wavename['N']:
                    qrs.append(itv)
                elif w.name == self._symbol_to_wavename['t']:
                    t_waves.append(itv)
        palette = {'p_waves': 'green', 'qrs': 'red', 't_waves': 'pink',}
        plot_alpha = 0.4

        diagnoses = self.load_diagnoses(rec)

        nb_leads = len(_leads)

        seg_len = self.freq * 25  # 25 seconds
        nb_segs = _data.shape[1] // seg_len

        t = np.arange(_data.shape[1]) / self.freq
        duration = len(t) / self.freq
        fig_sz_w = int(round(4.8 * duration))
        fig_sz_h = 6 * y_ranges / 1500
        fig, axes = plt.subplots(nb_leads, 1, sharex=True, figsize=(fig_sz_w, np.sum(fig_sz_h)))
        for idx in range(nb_leads):
            axes[idx].plot(t, _data[idx], label=f'lead - {self.all_leads[lead_indices[idx]]}')
            axes[idx].axhline(y=0, linestyle='-', linewidth='1.0', color='red')
            # NOTE that `Locator` has default `MAXTICKS` equal to 1000
            if ticks_granularity >= 1:
                axes[idx].xaxis.set_major_locator(plt.MultipleLocator(0.2))
                axes[idx].yaxis.set_major_locator(plt.MultipleLocator(500))
                axes[idx].grid(which='major', linestyle='-', linewidth='0.5', color='red')
            if ticks_granularity >= 2:
                axes[idx].xaxis.set_minor_locator(plt.MultipleLocator(0.04))
                axes[idx].yaxis.set_minor_locator(plt.MultipleLocator(100))
                axes[idx].grid(which='minor', linestyle=':', linewidth='0.5', color='black')
            # add extra info. to legend
            # https://stackoverflow.com/questions/16826711/is-it-possible-to-add-a-string-as-a-legend-item-in-matplotlib
            for d in diagnoses:
                axes[idx].plot([], [], ' ', label=d)
            for w in ['p_waves', 'qrs', 't_waves']:
                for itv in eval(w):
                    axes[idx].axvspan(itv[0], itv[1], color=palette[w], alpha=plot_alpha)
            axes[idx].legend(loc='upper left')
            axes[idx].set_xlim(t[0], t[-1])
            axes[idx].set_ylim(-y_ranges[idx], y_ranges[idx])
            axes[idx].set_xlabel('Time [s]')
            axes[idx].set_ylabel('Voltage [μV]')
        plt.subplots_adjust(hspace=0.2)
        plt.show()


    def _auto_infer_units(self, data:np.ndarray) -> str:
        """ finished, checked

        automatically infer the units of `data`,
        under the assumption that `data` not raw data, with baseline removed

        Parameters:
        -----------
        data: ndarray,
            the data to infer its units

        Returns:
        --------
        units: str,
            units of `data`, 'μV' or 'mV'
        """
        _MAX_mV = 20  # 20mV, seldom an ECG device has range larger than this value
        max_val = np.max(np.abs(data))
        if max_val > _MAX_mV:
            units = 'μV'
        else:
            units = 'mV'
        return units


    def database_info(self) -> NoReturn:
        """

        """
        print(self.__doc__)