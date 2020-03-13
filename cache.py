class Analyzer:
    @overload
    async def process_image(self, __data: bytes, __content_type: str) -> Image:
        pass
    @overload
    async def process_image(self, __url: str) -> Image:
        pass
    async def process_image(self, arg: Union[bytes, str], content_type: str = '') -> Image:
        """TODO."""
