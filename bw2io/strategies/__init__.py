from .ecospold1_allocation import allocate_ecospold1_datasets
from .generic import (
    assign_only_product_as_reference_product,
    link_biosphere_by_activity_hash,
    link_internal_technosphere_by_activity_hash,
    mark_unlinked_exchanges,
)
from .simapro import (
    link_based_on_name_and_unit,
    sp_allocate_products,
    split_simapro_name_geo,
)
from .ecospold2 import (
    assign_single_product_as_activity,
    create_composite_code,
    delete_exchanges_missing_activity,
    es2_assign_only_product_with_amount_as_reference_product,
    link_biosphere_by_flow_uuid,
    link_internal_technosphere_by_composite_code,
    remove_zero_amount_coproducts,
    remove_zero_amount_inputs_with_no_activity,
)