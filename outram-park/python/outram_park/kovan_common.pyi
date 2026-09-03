"""Type stubs for `outram_park.kovan_common`, generated from the Rust API.

Physical quantities cross this boundary as `float` in SI base units.
"""

class Author:
    family: str
    given: str
    affiliation: str | None
    def __init__(self, family: str, given: str, affiliation: str | None) -> None: ...

class DocumentType:
    @staticmethod
    def Paper() -> DocumentType: ...
    @staticmethod
    def Report() -> DocumentType: ...
    @staticmethod
    def Standard() -> DocumentType: ...
    @staticmethod
    def Benchmark() -> DocumentType: ...
    @staticmethod
    def Manual() -> DocumentType: ...
    @staticmethod
    def Thesis() -> DocumentType: ...
    @staticmethod
    def Other() -> DocumentType: ...
    def variant(self) -> str: ...

class GeneratedArtifact:
    method: str
    source: str
    correlation_id: str | None
    source_document_id: str | None
    def __init__(self, method: str, source: str, correlation_id: str | None, source_document_id: str | None) -> None: ...

class KovanBenchmark:
    id: str
    name: str
    source_document_id: str | None
    def __init__(self, id: str, name: str, source_document_id: str | None) -> None: ...

class KovanCorrelation:
    id: str
    name: str
    source_document_id: str | None
    def __init__(self, id: str, name: str, source_document_id: str | None) -> None: ...

class KovanDocument:
    id: str
    slug: str
    visibility: Visibility
    document_type: DocumentType
    title: str
    authors: list[Author]
    abstract_text: str
    year: int | None
    doi: str | None
    journal: str | None
    institution: str | None
    publisher: str | None
    volume: str | None
    pages: str | None
    number: str | None
    keywords: list[str]
    tags: list[str]
    source_url: str | None
    source_path: str | None
    source_sha256: str | None
    page_count: int | None
    assets: list[str]
    related_symbols: list[str]
    related_repositories: list[str]
    related_benchmarks: list[str]
    markdown_body: str
    def __init__(self, id: str, slug: str, visibility: Visibility, document_type: DocumentType, title: str, authors: list[Author], abstract_text: str, year: int | None, doi: str | None, journal: str | None, institution: str | None, publisher: str | None, volume: str | None, pages: str | None, number: str | None, keywords: list[str], tags: list[str], source_url: str | None, source_path: str | None, source_sha256: str | None, page_count: int | None, assets: list[str], related_symbols: list[str], related_repositories: list[str], related_benchmarks: list[str], markdown_body: str) -> None: ...

class KovanDocumentBuilder:
    def author(self, author: Author) -> KovanDocumentBuilder: ...
    def authors(self, authors: list[Author]) -> KovanDocumentBuilder: ...
    def year(self, year: int) -> KovanDocumentBuilder: ...
    def keywords(self, keywords: list[str]) -> KovanDocumentBuilder: ...
    def tags(self, tags: list[str]) -> KovanDocumentBuilder: ...
    def page_count(self, pages: int) -> KovanDocumentBuilder: ...
    def assets(self, assets: list[str]) -> KovanDocumentBuilder: ...
    def related_symbols(self, ids: list[str]) -> KovanDocumentBuilder: ...
    def related_repositories(self, ids: list[str]) -> KovanDocumentBuilder: ...
    def related_benchmarks(self, ids: list[str]) -> KovanDocumentBuilder: ...
    def build(self) -> KovanDocument: ...

class KovanRepository:
    id: str
    name: str
    language: str
    def __init__(self, id: str, name: str, language: str) -> None: ...

class KovanSymbol:
    id: str
    qualified_name: str
    kind: str
    repository_id: str
    file: str
    line: int
    language: Language
    def __init__(self, id: str, qualified_name: str, kind: str, repository_id: str, file: str, line: int, language: Language) -> None: ...

class KovanValidationCase:
    id: str
    name: str
    benchmark_id: str | None
    implementation_symbol_id: str | None
    def __init__(self, id: str, name: str, benchmark_id: str | None, implementation_symbol_id: str | None) -> None: ...

class Language:
    def as_str(self) -> str: ...
    @staticmethod
    def Rust() -> Language: ...
    @staticmethod
    def Cpp() -> Language: ...
    @staticmethod
    def Python() -> Language: ...
    @staticmethod
    def Fortran() -> Language: ...
    def variant(self) -> str: ...

class Visibility:
    @staticmethod
    def Open() -> Visibility: ...
    @staticmethod
    def Proprietary() -> Visibility: ...
    def variant(self) -> str: ...
