from constants import QUERY_AQL_LIMIT

AQL_EXAMPLES_TEMPLATE = """
    # Tell me about gene SAMD11
    FOR gene IN genes
    FILTER gene.name == "SAMD11"
    LIMIT {offset}, {limit}
    RETURN gene

    # show me all the variants that is in chromosome 1, position at 10000000?
    WITH variants
    FOR v IN variants
    FILTER v.chr == "chr1" AND v.pos == 10000000
    LIMIT {offset}, {limit}
    RETURN v

    # Can you tell me the variant with SPDI of NC_000012.12:102855312:C:T is associated with what diseases?
    WITH variants, variants_diseases, ontology_terms
    FOR variant IN variants
        FILTER variant.spdi == 'NC_000012.12:102855312:C:T'
        FOR d IN variants_diseases
            FILTER d._from == variant._id
            LIMIT {offset}, {limit}
            RETURN DOCUMENT(d._to)

    # Show me all variants associated with cardiomyopathy
    WITH variants, variants_diseases, ontology_terms
    FOR o IN ontology_terms
        FILTER o.name == 'cardiomyopathy'
        FOR d IN variants_diseases
            FILTER d._to == o._id
            LIMIT {offset}, {limit}
            RETURN DOCUMENT(d._from)

    # What are the transcripts from the protein PARI_HUMAN?
    FOR p IN proteins
        FILTER 'PARI_HUMAN' IN p.uniprot_names
        FOR t IN transcripts_proteins
            FILTER t._to == p._id
            LIMIT {offset}, {limit}
            RETURN DOCUMENT(t._from)



    # what genomic elements overlap rs1047055?
    LET variant = FIRST(
    FOR v IN variants
        FILTER "rs1047055" in v.rsid
        RETURN { chr: v.chr, pos: v.pos}
    )
    FOR g IN genomic_elements OPTIONS { indexHint: "idx_mdi_prefix_chr_start_end", forceIndexHint: true }
        FILTER g.chr == variant.chr AND g.start <= variant.pos AND g.end > variant.pos
        LIMIT {offset}, {limit}
        RETURN DISTINCT g

    # For eQTL data, what variants are active in tissue that is part of heart.
    LET heartTerms = (
    FOR t IN ontology_terms
        FILTER t.name == "heart"
        FOR v, e IN 1..7 INBOUND t ontology_terms_ontology_terms
            FILTER e.name IN ["part of"]
            RETURN DISTINCT v._id
    )
    FOR vg IN variants_genes
        FILTER vg.biosample_term IN heartTerms AND vg.label == "eQTL"
        LIMIT {offset}, {limit}
        RETURN DISTINCT {
            term: DOCUMENT(vg.biosample_term),
            variant: vg._from,
            gene: DOCUMENT(vg._to)
        }

    # Find the genomic elements that are linked to PP1F (ENSG00000187642), with score >0.85
    WITH genomic_elements, genomic_elements_genes
    FOR gene IN genomic_elements_genes
        FILTER gene._to == "genes/ENSG00000187642" AND gene.score > 0.85
        LIMIT {offset}, {limit}
        RETURN DOCUMENT(gene._from)

    # Find eQTLs in ontology term named amygdala.
    LET amygdalaTerms = (
    FOR t IN ontology_terms
        FILTER t.name == "amygdala"
        RETURN t._id
    )
    FOR vg IN variants_genes
        FILTER vg.biosample_term IN amygdalaTerms AND vg.method == "eQTL"
        LIMIT {offset}, {limit}
        LET gene = DOCUMENT(vg._to)
        LET variant = DOCUMENT(vg._from)
    RETURN {'p-val': vg.`p_value`,
            'biosample': vg.biological_context,
            'gene': gene.name,
            'variant': variant.spdi}

    # For variant with rsID rs309428, find the genomic elements that it is contained in.
    LET variant = FIRST(
        FOR v IN variants
            FILTER "rs309428" in v.rsid
            RETURN v
    )
    FOR g IN genomic_elements OPTIONS { indexHint: "idx_mdi_prefix_chr_start_end", forceIndexHint: true }
        FILTER g.chr == variant.chr AND g.start <= variant.pos AND g.end > variant.pos
        LIMIT {offset}, {limit}
        RETURN g

    # Find the top genes that are co-expressed with gene ENSG00000261221, sorted by z_score.
    FOR gg in genes_genes
        FILTER gg._from == 'genes/ENSG00000261221'
        SORT gg.`z_score` ASC
        LIMIT {offset}, {limit}
        RETURN gg

    # Find genes that are linked to variant with SPDI NC_000017.11:76710350:G:A.
    LET variant = FIRST(
        FOR v IN variants
            FILTER v.spdi == 'NC_000017.11:76710350:G:A'
            RETURN v
    )
    FOR vg IN variants_genes
        FILTER vg._from == variant._id
        LIMIT {offset}, {limit}
        RETURN DISTINCT DOCUMENT(vg._to)

    # Is variant with rsID rs875741 a caQTL?
    FOR v in variants
        FILTER "rs875741" in v.rsid
    FOR vg IN variants_genomic_elements
        FILTER vg._from == v._id
        LIMIT {offset}, {limit}
        return vg

    # find variants linked to gene ENSG00000188290.
    FOR vg IN variants_genes
        FILTER vg._to == 'genes/ENSG00000188290'
        LIMIT {offset}, {limit}
        RETURN DOCUMENT(vg._from)

    # What diseases are associated with gene PAH?
    FOR gene IN genes
        FILTER gene.name == "PAH"
        FOR edge IN diseases_genes
            FILTER edge._to == gene._id
            LIMIT {offset}, {limit}
            RETURN DOCUMENT(edge._from)
    """


def get_aql_examples(limit, offset=0):
    return (
        AQL_EXAMPLES_TEMPLATE
        .replace('{offset}', str(offset))
        .replace('{limit}', str(limit))
    )


AQL_EXAMPLES = get_aql_examples(limit=QUERY_AQL_LIMIT, offset=0)
