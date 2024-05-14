import logging

import pandas as pd
from time import monotonic
from data_handler.handlers.loan_states.abstractions import LoanStateComputationBase
from data_handler.handlers.loan_states.nostra_alpha.events import NostraAlphaState
from data_handler.tools.constants import ProtocolAddresses, ProtocolIDs

logger = logging.getLogger(__name__)


class NostraAlphaStateComputation(LoanStateComputationBase):
    """
    A class that computes the loan states for the NOSTRA_ALPHA protocol.
    """

    PROTOCOL_TYPE = ProtocolIDs.NOSTRA_ALPHA.value
    PROTOCOL_ADDRESSES = ProtocolAddresses().NOSTRA_ALPHA_ADDRESSES

    def get_data(self, form_address: str, min_block: int) -> dict:
        """
        Fetches data from the DeRisk API endpoint using the defined protocol address.
        This method must be implemented by subclasses to specify how data is retrieved from the API.

        :param form_address: The address of the contract from which to retrieve events.
        :type form_address: str
        :param min_block: The minimum block number from which to retrieve events.
        :type min_block: int
        """
        logger.info(
            f"Fetching data from {self.last_block} to {min_block + self.PAGINATION_SIZE} for address {form_address}"
        )
        return self.api_connector.get_data(
            from_address=form_address,
            min_block_number=self.last_block,
            max_block_number=min_block + self.PAGINATION_SIZE,
        )

    def process_data(self, data: list[dict]) -> pd.DataFrame:
        """
        Processes the data retrieved from the DeRisk API.
        This method must be implemented by subclasses to define the data processing steps.

        :param data: The data retrieved from the DeRisk API.
        :type data: list[dict]

        :return: pd.DataFrame
        """
        nostra_alpha_state = NostraAlphaState()
        events_mapping = nostra_alpha_state.EVENTS_METHODS_MAPPING
        # Init DataFrame
        df = pd.DataFrame(data)
        # Filter out events that are not in the mapping
        df_filtered = df[df["key_name"].isin(events_mapping.keys())]
        for index, row in df_filtered.iterrows():
            method_name = events_mapping.get(row["key_name"], "") or ""
            self.process_event(nostra_alpha_state, method_name, row)

        result_df = self.get_result_df(nostra_alpha_state.loan_entities)
        return result_df

    def run(self) -> None:
        """
        Runs the loan state computation for the NOSTRA_ALPHA protocol.
        """
        retry = 0
        max_retries = 5
        for protocol_address in self.PROTOCOL_ADDRESSES:
            while True:
                data = self.get_data(protocol_address, self.last_block)
                if not data and retry < max_retries:
                    self.last_block += self.PAGINATION_SIZE
                    retry += 1
                    continue
                elif retry == max_retries:
                    break

                processed_data = self.process_data(data)
                self.save_data(processed_data)
                self.last_block += self.PAGINATION_SIZE
                logger.info(f"Processed data up to block {self.last_block}")


def run_loan_states_computation_for_nostra_alpha() -> None:
    """
    Runs the NOSTRA_ALPHA loan state computation.
    """
    start = monotonic()
    logging.basicConfig(level=logging.INFO)

    logger.info("Starting NostraAlpha loan state computation")
    computation = NostraAlphaStateComputation()
    computation.run()

    logger.info(
        "Finished NostraAlpha  loan state computation, Time taken: %s seconds",
        monotonic() - start,
    )


if __name__ == "__main__":
    run_loan_states_computation_for_nostra_alpha()
