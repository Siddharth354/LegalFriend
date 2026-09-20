SOURCE_URLS_BY_ACT: dict[str, str] = {
    "Bharatiya Nyaya Sanhita, 2023": "https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf",
    "Negotiable Instruments Act, 1881": "https://www.indiacode.nic.in/bitstream/123456789/15327/1/negotiable_instruments_act,_1881.pdf",
    "Reserve Bank of India (Digital Lending) Directions, 2025": "https://www.axis.bank.in/docs/default-source/default-document-library/reserve-bank-of-india-digital-lending-directions2025.pdf?sfvrsn=864862e_1",
    "RBI Recovery Agents Circular, 2022": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12378&Mode=0",
    "Usurious Loans Act, 1918": "https://www.indiacode.nic.in/bitstream/123456789/2362/1/A1918-10.pdf",
}


def source_url_for_act(act: str) -> str:
    return SOURCE_URLS_BY_ACT.get(act, "")
