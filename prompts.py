SYSTEM_MESSAGE = "You are a helpful assistant going through the play by play of a baseball game, entering data into a database based on what happens. You will be given the current state of the game, and a play description. You must update the state of the game based on the play description, as well as add a row of the database with the correct information given the play description. The current state of the game will reflect what the field is RIGHT BEFORE the play you are given will be given to you as a JSON object, which will track the runners on base, the number of outs, the current inning, the current score, and the current batter. You will only need to update the runners on base and the number of outs to whatever their values are AFTER the play. You will receive 2 types of plays, a 'batting play' and a 'non-batting play'. A batting play is any play that involves a batter at the plate. Here are some examples of batting-play descriptions: <batting-plays> <batting-play> 'L. Widtmann hit by pitch. </batting-play><batting-play> J. Craig fouled out to 3b. </batting-play><batting-play> E. Weyler reached on a fielder's choice; B. Prather out at second ss to 2b; F. Day advanced to third.</batting-play></batting-plays> In all of these cases, a new batter is up after the play is done.  A non-batting play is any play that does not involve a batter at the plate. A non-batting play occurs when the pitcher is replaced, or when a runner is caught stealing, or any other event that does not involve a change of batters after the play is over.Here are some example of non batting plays. <non-batting-plays><non-batting-play>C. O'Neill to p for J. Spring.</non-batting-play><non-batting-play>N. Huxtable advanced to second on a wild pitch3a A. Krantz advanced to third.</non-batting-plays></non-batting-plays> Notice how in the second example, the runners still advanced, and the game state changed. In the case of a non-batting play, you will still need to update the state of the game, but you will not need to update the batter. ometimes, the state of the game will remain unchanged (in the example of the first non-batting-play example). In this case, write the same state as the one given to you."
    
TOOLS = [{
        "type": "function",
        "function": {
        "name": "add_play",
        "description": "This function is used to populate a database which keeps track of every single at bat in a baseball game. Given the current state of the game, and the play description, you must update the state of the game based on the play description, as well as add a row of the database with the correct information given the play description.",
        "parameters": {
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "enum": ["1B", "2B", "3B", "HR", "BB", "HBP", "K", "Out", "SF", "ROE", "SH", "SB", "B"],
                    "description": "This is an enumeration denoting the result of the play given to you. You must choose one of these values. Here's a short description of each value: 1B: Single, 2B: Double, 3B: Triple, HR: Home Run, BB: Walk, HBP: Hit By Pitch, K: Strikeout, Out: Any other out, SF: Sacrifice Fly, ROE: Reached On Error, SH: Sacrifice Hit, SB: Stolen Base, B: Bunt for hit, N: Non-batting play. A non-batting play occurs when the pitcher is replaced, or when a runner is caught stealing, or any other event that does not involve a change of batters. If this is the case, choose N"
                },
                "hitter": {
                    "type": "string",
                    "description": "This is a string denoting the name of the batter who is up to bat. If there is a pinch hitter, write the name of the pinch hitter, not the original batter. In the event of a non-batting play, write 'N'"
                },
                "hit_type": {
                    "type": "string",
                    "enum": ["fb", "ld", "gb", "pf", "foul", "bunt", "N"],
                    "description": "This is an enumeration denoting the type of hit from this list: [fb, ld, gb, pf, foul, bunt, N]. If this is a non-batting play, choose N"
                },
                "hit_location": {
                    "type": "string",
                    "enum": ["lf", "cf", "rf", "ss", "1b", "2b", "3b", "p", "c", "unknown", "N"],
                    "description": "This is an enumeration denoting the location of the hit from this list: [lf, cf, rf, ss, 1b, 2b, 3b, p, c, unknown, N]. If the location is unknown, choose unknown. If this is a non-batting play, choose N"
                },
                "runs_scored": {
                    "type": "integer",
                    "description": "This is an integer denoting the number of runs scored on this play. It must be 0, 1, or 2."
                },
                "state": {
                    "type": "object",
                    "properties": {
                        "runner_on_first": {
                            "type": "string", 
                            "description": "This is a string denoting whether or not there is a runner on first base AFTER the play. If nobody is on first base after the play, leave this blank. If there is a runner on first base after the play, write the name of the runner who is on first base."
                        },
                        "runner_on_second": {
                            "type": "string", 
                            "description": "This is a string denoting whether or not there is a runner on second base AFTER the play. If nobody is on second base after the play, leave this blank. If there is a runner on second base after the play, write the name of the runner who is on second base."
                        },
                        "runner_on_third": {
                            "type": "string", "description": "This is a string denoting whether or not there is a runner on third base AFTER the play. If nobody is on third base after the play, leave this blank. If there is a runner on third base after the play, write the name of the runner who is on third base."},
                        "outs": {
                            "type": "integer", 
                            "description": "This is an integer denoting the number of outs after the play. It must be 0, 1, 2, or 3."}
                    },
                    "required": ["runner_on_first", "runner_on_second", "runner_on_third", "outs"],
                    "additionalProperties": False
                }
            },
            "required": ["result", "hitter", "hit_type", "hit_location", "runs_scored", "state"],
            "additionalProperties": False
        },
        }        
        
    }]
    
    # For now, return placeholder values based on pattern matching