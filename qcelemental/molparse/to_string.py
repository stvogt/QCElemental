import collections

import numpy as np

import qcelemental as qcel

def to_string(molrec, dtype, units='Angstrom', atom_format=None, ghost_format=None, width=17, prec=12): #, return_options=False):
    """Format a string representation of QM molecule.

    Parameters
    ----------
    molrec : dict
        Psi4 json Molecule spec.
    dtype : {'xyz'}
        Overall string format. Note that it's possible to request variations
        that don't fit the dtype spec so may not be re-readable (e.g., ghost
        and mass in nucleus label with 'xyz').
        'cfour' forces nucleus label, ignorming atom_format, ghost_format
    units : {'Angstrom', 'Bohr'}
        Units in which to write string. There is not an option to write in
        intrinsic/input units. For `dtype='xyz', units='Bohr'` where the
        format doesn't have a slot to specify units, "au" is added so that
        readable as 'xyz+'.
    atom_format : str, optional
        General format is '{elem}'. A format string that may contain fields
        'elea' (-1 will be ''), 'elez', 'elem', 'mass', 'elbl' in any
        arrangement. For example if a format naturally uses element symbol
        and you want atomic number instead with mass info, too, pass
        '{elez}@{mass}'. See `ghost_format` for handling field 'real'.
    ghost_format : str, optional
        General format is '@{elem}'. Like `atom_format`, but this formatter
        is used when `real=False`. To suppress ghost atoms, use `ghost_format=''`.
    width : int, optional
        Field width for formatting coordinate float.
    prec : int, optional
        Number of decimal places for formatting coordinate float.
#    return_options : bool, optional
#        Some dtypes (cfour) can also return options knowable from `molrec`

    Returns
    -------
    smol : str
        String representation of the molecule.
#    opts : dict
#        Only when `return_options=True`Some formats (cfour) can also return options

    """

    #funits, fiutau = process_units(molrec)
    #molrec = self.to_dict(force_units=units, np_out=True)

    if molrec['units'] == 'Angstrom' and units == 'Angstrom':
        factor = 1.
    elif molrec['units'] == 'Angstrom' and units == 'Bohr':
        if 'input_units_to_au' in molrec:
            factor = molrec['input_units_to_au']
        else:
            factor = 1. / qcel.constants.bohr2angstroms
    elif molrec['units'] == 'Bohr' and units == 'Angstrom':
        factor = qcel.constants.bohr2angstroms
    elif molrec['units'] == 'Bohr' and units == 'Bohr':
        factor = 1.
    else:
        raise ValidationError("""units must be 'Angstrom'/'Bohr', not {}""".format(units))
    geom = np.array(molrec['geom']).reshape((-1, 3)) * factor

    name = molrec.get('name', formula_generator(molrec['elem']))
    tagline = """auto-generated by qcdb from molecule {}""".format(name)

    if dtype == 'xyz':
        atom_format = '{elem}' if atom_format is None else atom_format
        ghost_format = '@{elem}' if ghost_format is None else ghost_format

        atoms = _atoms_formatter(molrec, geom, atom_format, ghost_format, width, prec, 2)
        nat = len(atoms)

        first_line = """{}{}""".format(str(nat), ' au' if units == 'Bohr' else '')
        smol = [first_line, name]
        smol.extend(atoms)

    elif dtype == 'cfour':
        # Notes
        # * losing identity of ghost atoms. picked up again in basis formatting
        # * casting 'molecular_charge' to int
        # * no spaces at the beginning of 1st/comment line is important

        atom_format = '{elem}'
        ghost_format = 'GH'

        atoms = _atoms_formatter(molrec, geom, atom_format, ghost_format, width, prec, 2)

        smol = [tagline]
        smol.extend(atoms)

    elif dtype == 'nwchem':

        atom_format = '{elem}'
        ghost_format = 'GH'

        atoms = _atoms_formatter(molrec, geom, atom_format, ghost_format, width, prec, 2)

        first_line = """geometry units {}""".format(units.lower())
        # noautosym nocenter  # no reorienting input geometry
        fix_symm = molrec.get('fix_symmetry', None)
        symm_line = ''
        if fix_symm:
            symm_line = 'symmetry {}'.format(fix_symm)  # not quite what Jiyoung had
        last_line = """end"""
        smol = [first_line]
        smol.extend(atoms)
        smol.append(symm_line)
        smol.append(last_line)

    return '\n'.join(smol) + '\n'


def _atoms_formatter(molrec, geom, atom_format, ghost_format, width, prec, sp):
    """Format a list of strings, one per atom from `molrec`."""

    #geom = molrec['geom'].reshape((-1, 3))
    nat = geom.shape[0]
    fxyz = """{:>{width}.{prec}f}"""
    sp = """{:{sp}}""".format('', sp=sp)

    atoms = []
    for iat in range(nat):
        atom = []
        atominfo = {'elea': '' if molrec['elea'][iat] == -1 else molrec['elea'][iat],
                    'elez': molrec['elez'][iat],
                    'elem': molrec['elem'][iat],
                    'mass': molrec['mass'][iat],
                    'elbl': molrec['elbl'][iat]}

        if molrec['real'][iat]:
            nuc = """{:{width}}""".format(atom_format.format(**atominfo), width=width)
            atom.append(nuc)
        else:
            if ghost_format == '':
                continue
            else:
                nuc = """{:{width}}""".format(ghost_format.format(**atominfo), width=width)
                atom.append(nuc)

        atom.extend([fxyz.format(x, width=width, prec=prec) for x in geom[iat]])
        atoms.append(sp.join(atom))

    return atoms


def formula_generator(elem):
    """Return simple chemical formula from element list `elem`.

    >>> formula_generator(['C', 'Ca', 'O', 'O', 'Ag']
    AgCCaO2

    """
    counted = collections.Counter(elem)
    return ''.join((el if cnt == 1 else (el + str(cnt))) for el, cnt in sorted(counted.items()))


if __name__ == '__main__':
    formula_generator(['C', 'Ca', 'O', 'O', 'Ag'])

