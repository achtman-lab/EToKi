import os, sys, hashlib, numpy as np
from subprocess import Popen, PIPE
from configure import externals, logger, transeq
from operator import itemgetter

parameters = dict(
    prefix = 'MLSTdb',
	reIndex = True,
    fasta = [],
    id = 0.85,
    n_thread = 7,
)

parameters.update(externals)

def mmseq_cluster(prefix, genes, id) :
    import shutil, glob

    subprocess.Popen('{0} createdb {2} {1}.db -v 0'.format(params['mmseqs'], prefix, genes).split()).communicate()
    if not os.path.isdir(prefix + '.tmp') :
        os.makedirs(prefix + '.tmp')
    if os.path.isfile(prefix + '.lc') :
        for fname in glob.glob(prefix+'.lc*') :
            try : 
                os.unlink(fname)
            except :
                pass
    subprocess.Popen('{0} cluster {1}.db {1}.lc {1}.tmp --min-seq-id {2} --threads {4} -v 0'.format(params['mmseqs'], prefix, id, params['n_thread']).split()).communicate()
    subprocess.Popen('{0} result2repseq {1}.db {1}.lc {1}.rep --threads {2} -v 0'.format(params['mmseqs'], prefix, params['n_thread']).split()).communicate()
    subprocess.Popen('{0} result2flat {1}.db {1}.db {1}.rep {1}.reference --use-fasta-header -v 0'.format(params['mmseqs'], prefix, params['n_thread']).split()).communicate()
    shutil.rmtree(prefix + '.tmp')
    for fn in (prefix+'.db*', prefix+'.lc*', prefix+'.rep*') :
        for fname in glob.glob(fn) :
            try :
                os.unlink(fname)
            except :
                pass
    return '{0}.reference'.format(prefix)


def readFastaToList(fnames) :
    if isinstance(fnames, basestring) :
        fnames = [fnames]
    seq = []
    fin = Popen(['zcat'] + fnames, stdout=PIPE) if fnames[0][-3:].lower() == '.gz' else Popen(['cat'] + fnames, stdout=PIPE)
    for line in fin.stdout:
        if line[0] == '>' :
            name = line[1:].strip().split()[0]
            seq.append([name, []])
        else :
            seq[-1][1].extend( line.strip().split() )
    fin.stdout.close()
    for s in seq:
        s[1] = ''.join( s[1] )
    return seq

def MLSTdb() :
    for arg in sys.argv[1:] :
        if arg.find('=') >= 0 :
            k, v = arg.split('=', 1)
            if k in parameters :
                parameters[k] = v
        else :
            parameters['fasta'].append(arg)

    alleles = readFastaToList(parameters['fasta'])
    loci = { allele_id.rsplit('_', 1)[0]:[] for allele_id, seq in alleles }
    for allele_id, seq in alleles :
        locus, id = allele_id.rsplit('_', 1)
        loci[locus].append([id, seq])
    del alleles

    with open('{0}.refset.fna'.format(parameters['prefix']), 'w') as refout :
        for locus, alleles in loci.iteritems() :
            with open('{0}.refset'.format(parameters['prefix']), 'w') as fout :
                id, seq = alleles[0]
                fout.write('>{0}\n{1}\n'.format(id, seq))
            with open('{0}.alleles'.format(parameters['prefix']), 'w') as fout :
                for id, seq in alleles[1:] :
                    fout.write('>{0}\n{1}\n'.format(id, seq))

            format_cmd = '{formatdb} -dbtype nucl -in {prefix}.refset'.format(**parameters)
            Popen(format_cmd.split(), stderr=PIPE, stdout=PIPE).communicate()
            blast_cmd = '{blast} -db {prefix}.refset -query {prefix}.alleles -outfmt "6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue score qlen slen" -num_threads 6 -task blastn -evalue 1e-3 -dbsize 5000000 -reward 2 -penalty -2 -gapopen 6 -gapextend 2'.format(
                **parameters
            )
            p = Popen(blast_cmd, stderr=PIPE, stdout=PIPE, shell=True)

            ids = {alleles[0][0]: 1}
            for line in p.stdout :
                p = np.array(line.strip().split(), dtype=float)
                if p[6] - 1 < 10 and p[6] == p[8] and p[12] - p[7] < 10 and p[13] - p[9] == p[12] - p[7] :
                    ids[str(int(p[0]))] = 1
            with open('{0}.alleles'.format(parameters['prefix']), 'w') as fout :
                for id, seq in alleles :
                    if id in ids :
                        fout.write('>{0}_{1}\n{2}\n'.format(locus, id, seq))
            outfile = mmseq_cluster(parameters['prefix'], parameters['prefix'] + '.alleles', parameters['id'])
            with open(outfile) as fin :
                for line in fin :
                    refout.write(line)
    refseq = readFastaToList('{0}.refset.fna'.format(parameters['prefix']))
    ref_aa = transeq(dict(refseq))
    with open('{0}.refset.faa'.format(parameters['prefix']), 'w') as fout :
        for n, s in ref_aa.iteritems() :
            if s[:-1].find('X') < 0 :
                fout.write( '>{0}\n{1}\n'.format(n, s) )
    return '{0}.refset.fna'.format(parameters['prefix']), '{0}.refset.faa'.format(parameters['prefix'])

if __name__ == '__main__' :
    MLSTdb()