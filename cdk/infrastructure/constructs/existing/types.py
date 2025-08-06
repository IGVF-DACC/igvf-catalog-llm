from infrastructure.constructs.existing.catalog_llm_dev import Resources as CatalogLLMDevResources
from infrastructure.constructs.existing.catalog_llm_prod import Resources as CatalogLLMProdResources

from typing import Union

from typing import Type


ExistingResources = Union[
    CatalogLLMDevResources,
    CatalogLLMProdResources,
]

ExistingResourcesClass = Union[
    Type[CatalogLLMDevResources],
    Type[CatalogLLMProdResources],
]
