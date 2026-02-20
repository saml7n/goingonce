// API types matching server schemas

export interface Auction {
  id: string;
  item_name: string;
  starting_price: number;
  current_price: number;
  current_bidder_id: string | null;
  current_bidder_name: string | null;
  end_time: string;
  status: "active" | "ended";
  created_at: string;
}

export interface Bid {
  id: string;
  bidder_id: string;
  bidder_name: string;
  amount: number;
  created_at: string;
}

export interface AuctionDetail extends Auction {
  bids: Bid[];
}

export interface BidResult {
  success: boolean;
  message: string;
  auction: Auction;
  bid: Bid | null;
}

// WebSocket message types
export type WSMessage =
  | WSStateMessage
  | WSNewBidMessage
  | WSOutbidMessage
  | WSTimeExtendedMessage
  | WSAuctionEndedMessage
  | WSPongMessage
  | WSErrorMessage;

export interface WSStateMessage {
  type: "state";
  auction: Auction;
  bids: Bid[];
  server_time: string;
}

export interface WSNewBidMessage {
  type: "new_bid";
  bid: Bid;
  auction: {
    current_price: number;
    current_bidder_id: string;
    current_bidder_name: string;
    end_time: string;
  };
  server_time: string;
}

export interface WSOutbidMessage {
  type: "outbid";
  by: string;
  new_price: number;
  server_time: string;
}

export interface WSTimeExtendedMessage {
  type: "time_extended";
  new_end_time: string;
  server_time: string;
}

export interface WSAuctionEndedMessage {
  type: "auction_ended";
  auction: Auction;
  winner_id: string | null;
  winner_name: string | null;
  final_price: number;
  server_time: string;
}

export interface WSPongMessage {
  type: "pong";
  server_time: string;
}

export interface WSErrorMessage {
  type: "error";
  message: string;
}
