import abc
from typing import Optional, List, Union
from pydantic import BaseModel, Field


class Chunk:
    content: str
    similarity: float

    def __init__(self, content: str, similarity: float):
        self.content = content
        self.similarity = similarity


class Document:
    """
    Document is a class that represents a document.
    """

    id: str
    url: Optional[str] = None
    title: Optional[str] = None
    chunks: List[Chunk] = []

    def __init__(
        self,
        id: str,
        url: Optional[str] = None,
        title: Optional[str] = None,
        chunks: List[Chunk] = [],
    ):
        self.id = id
        self.url = url
        self.title = title
        self.chunks = chunks

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "content": "\n\n".join([chunk.content for chunk in self.chunks]),
        }
        if self.url:
            d["url"] = self.url
        if self.title:
            d["title"] = self.title
        return d


class Resource(BaseModel):
    """
    Resource is a class that represents a resource.
    """

    uri: str = Field(..., description="The URI of the resource")
    title: str = Field(..., description="The title of the resource")
    description: Optional[str] = Field(
        "", description="The description of the resource"
    )


class Retriever(abc.ABC):
    """
    Define a RAG provider, which can be used to query documents and resources.
    """

    @abc.abstractmethod
    def list_resources(self, query: Optional[str] = None) -> List[Resource]:
        """
        List resources from the rag provider.
        """
        pass

    @abc.abstractmethod
    def query_relevant_documents(
        self, query: str, resources: List[Resource] = []
    ) -> List[Document]:
        """
        Query relevant documents from the resources.
        """
        pass
